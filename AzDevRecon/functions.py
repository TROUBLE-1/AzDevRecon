from AzDevRecon.models import AccessTokenSubmission, db
import re, base64, requests, json
import concurrent.futures

def identify_token_type(token):
    jwt_pattern = r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$"

    if re.match(jwt_pattern, token):
        return "Token"
    else:
        return "PAT"

def check_if_token_is_valid(token, organization):
    headers = {"Authorization": token}
    url = f"https://dev.azure.com/{organization}/_apis/?api-version=7.1"
    res = requests.get(url, headers=headers)
    return True if res.status_code == 200  else  False

def add_submission(token, organization_name, user_id):

    identify_token = identify_token_type(token)
    if identify_token == "PAT":
        pat = f"{token}:"
        pat_string_bytes = pat.encode("ascii")
        base64_bytes = base64.b64encode(pat_string_bytes)
        base64_token = base64_bytes.decode("ascii")
        token = f"Basic {base64_token}"
    elif identify_token == "Token":
        token = f"Bearer {token}"
    else:
        return "danger", "Invalid PAT/Access Token"
    
    if check_if_token_is_valid(token, organization_name) == False:
        return "danger", "Token is invalid or Expired!"
    
    try:
        # Create a new submission instance
        new_submission = AccessTokenSubmission(user_id=user_id, token=token, organization_name=organization_name )

        # Add to database and commit
        db.session.add(new_submission)  # type: ignore
        db.session.commit()  # type: ignore
        
        return "success", "Token submitted successfully!"
    except Exception as e:
        db.session.rollback()  # type: ignore  # Rollback in case of any errors
        print(e)
        return "danger", (f"Failed to add submission: {e}")




def restAPI(url, token):
    res = requests.get(url, headers={"Authorization": token})
    if res.status_code == 200:
        return True, res.json()
    
    return False, "Token is Invalid!!"

def list_projects(org_name, token):
    url = f"https://dev.azure.com/{org_name}/_apis/projects?api-version=7.1"
    return restAPI(url, token)


def list_repos(org_name, project_name,token):
    url = f"https://dev.azure.com/{org_name}/{project_name}/_apis/git/repositories?api-version=7.1"
    return restAPI(url, token)

def list_repo_items(org_name, project_name, repo_id, token):
    url = f"https://dev.azure.com/{org_name}/{project_name}/_apis/git/repositories/{repo_id}/items?recursionLevel=1&api-version=7.1"
    return restAPI(url, token)



def get_org_users(org_name, token):
    url = f"https://vsaex.dev.azure.com/{org_name}/_apis/MemberEntitlements?%24filter=&%24orderBy=name%20Ascending"
    return restAPI(url, token)


def fetch_group_members(org_name, project, token, group):
    url = f"https://dev.azure.com/{org_name}/_apis/Contribution/HierarchyQuery?api-version=7.0-preview"
    descriptor = group["descriptor"]
    jsonObj1 = {
        "contributionIds": ["ms.vss-admin-web.org-admin-group-members-data-provider"],
        "dataProviderContext": {
            "properties": {
                "subjectDescriptor": descriptor,
                "sourcePage": {
                    "url": f"https://dev.azure.com/{org_name}/{project}/_settings/permissions?subjectDescriptor={descriptor}",
                    "routeId": "ms.vss-admin-web.project-admin-hub-route",
                    "routeValues": {
                        "project": project,
                        "adminPivot": "permissions",
                        "controller": "ContributedPage",
                        "action": "Execute"
                    }
                }
            }
        }
    }
    res = requests.post(url, json=jsonObj1, headers={"Authorization": token})
    if res.status_code == 200:
        members = res.json()["dataProviders"].get("ms.vss-admin-web.org-admin-group-members-data-provider", {}).get("identities", [])
        group["members"] = members

def get_project_permissions(org_name, project, token):
    url = f"https://dev.azure.com/{org_name}/_apis/Contribution/HierarchyQuery?api-version=7.0-preview"
    jsonObj = {
        "contributionIds": ["ms.vss-admin-web.org-admin-groups-data-provider"],
        "dataProviderContext": {
            "properties": {
                "sourcePage": {
                    "url": f"https://dev.azure.com/{org_name}/{project}/_settings/permissions",
                    "routeId": "ms.vss-admin-web.project-admin-hub-route",
                    "routeValues": {
                        "project": project,
                        "adminPivot": "permissions",
                        "controller": "ContributedPage",
                        "action": "Execute"
                    }
                }
            }
        }
    }
    res = requests.post(url, json=jsonObj, headers={"Authorization": token})
    if res.status_code == 200:
        groups = res.json()["dataProviders"].get("ms.vss-admin-web.org-admin-groups-data-provider", {}).get("identities", [])
    else:
        return []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(fetch_group_members, org_name, project, token, group) for group in groups]
        concurrent.futures.wait(futures)
    
    return groups


import requests

def get_project_workitems(org_name, project_name, token, work_item_type=None, state=None, assigned_to=None):
    wiql_query = "SELECT [System.Id] FROM WorkItems"

    wiql_body = { "query": wiql_query }

    wiql_url = f"https://dev.azure.com/{org_name}/{project_name}/_apis/wit/wiql?api-version=7.1"
    wiql_response = requests.post(wiql_url, json=wiql_body, headers={"Authorization": token})

    if wiql_response.status_code != 200:
        return False, f"Failed to query work items: {wiql_response.status_code}"

    wiql_data = wiql_response.json()
    work_items = wiql_data.get('workItems', [])

    if not work_items:
        return True, []

    work_item_ids = [str(item['id']) for item in work_items]

    all_details = []
    batch_size = 200

    for i in range(0, len(work_item_ids), batch_size):
        batch_ids = work_item_ids[i:i+batch_size]
        url = (
            f"https://dev.azure.com/{org_name}/{project_name}/_apis/wit/workitems"
            f"?ids={','.join(batch_ids)}&$expand=all&api-version=7.1"
        )
        response = requests.get(url, headers={"Authorization": token})

        if response.status_code != 200:
            return False, f"Failed to get work item details for batch starting at index {i}: {response.status_code}"

        items = response.json().get('value', [])
        all_details.extend(items)

    return True, all_details



def get_work_item_by_id(org_name, project_name, work_item_id, token):

    url = f"https://dev.azure.com/{org_name}/{project_name}/_apis/wit/workItems/{work_item_id}?$expand=all&api-version=7.1"
    return restAPI(url, token)


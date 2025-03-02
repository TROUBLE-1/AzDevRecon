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
        pat = f":{token}"
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
        db.session.add(new_submission)
        db.session.commit()
        
        return "success", "Token submitted successfully!"
    except Exception as e:
        db.session.rollback()  # Rollback in case of any errors
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
    url = f"https://dev.azure.com/{org_name}/{project_name}/_apis/git/repositories/{repo_id}/items?recursionLevel=Full&api-version=7.1"
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

token = "Basic OkcxM1l4c0pQNUoyOHRPaW40UTZDbXRzYk1FTkp2bTRhNll6eXVSd0FHYlZ5a3BHVFo3cndKUVFKOTlCQ0FDQUFBQUFGallDVkFBQVNBWkRPNEZEeg=="
org_name= "asgasga4t24t"
project = "wkl-prod"


get_project_permissions(org_name, project, token)
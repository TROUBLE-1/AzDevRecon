from AzDevRecon.models import AccessTokenSubmission, db
import re, base64, requests

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
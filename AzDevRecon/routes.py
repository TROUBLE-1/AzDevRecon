from flask import render_template, request, send_file, url_for, flash, abort, Response, jsonify
from numpy import append
from werkzeug.utils import redirect
from AzDevRecon import app, db, bcrypt, socketio, emit
from AzDevRecon.models import *
from sqlalchemy.sql import text
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
import flask, threading, uuid, json, yaml
from AzDevRecon.forms import *
from AzDevRecon.functions import *

db.create_all()

@app.route("/", methods=['GET', 'POST'])
def login():
    adminUser = User.query.all()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful!', 'danger')
    return render_template('login.html', title='Login', form=form, userexist=adminUser)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists! Please choose a different username.', 'danger')
            return render_template('register.html', title='Register', form=form)
        
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        id = uuid.uuid4().hex
        user = User(id=id, username=form.username.data, password=hashed_password)
        db.session.add(user)  # type: ignore
        db.session.commit()  # type: ignore
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/azure/devops/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    form = DashboardForm()
    submissions = AccessTokenSubmission.query.filter_by(user_id=current_user.id).all()
    
    if form.validate_on_submit():
        try:
            token = form.access_token.data
            organization_name = form.organization.data 
            add_status = add_submission(token, organization_name, current_user.id)
            flash(add_status[1], add_status[0])
            return redirect(url_for("dashboard"))
        except RuntimeError as e:
            flash(str(e), "danger")
    
    return render_template("dashboard.html", form=form, submissions=submissions)


@app.route("/azure/devops/<org_id>/projects", methods=["GET", "POST"])
@login_required
def view_projects(org_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    projects = list_projects(org_name.organization_name, org_name.token)
    if projects[0] == False:
        flash(projects[1], "danger")

    org_users = get_org_users(org_name.organization_name, org_name.token)
    if org_users[0] == False:
        org_users = []
    else:
        org_users = org_users[1]    
    
    
    return render_template("projectslist.html", organization_name=org_name.organization_name, projects=projects[1], json=json, members_data=org_users)


@app.route("/azure/devops/<org_id>/projects/<project>/permissions", methods=["GET", "POST"])
@login_required
def view_project_permissions(org_id, project):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    
    all_permissions = get_project_permissions(org_name.organization_name, project, org_name.token)

    return render_template("devops_projects/all_permissions.html", all_permissions=all_permissions, project_name=project)

@app.route("/azure/devops/<org_id>/projects/<project_id>", methods=["GET", "POST"])
@login_required
def project_dashboard(org_id, project_id):
    
    return render_template("devops_projects/project.html", org_id=org_id, project_id=project_id)


@app.route("/azure/devops/<org_id>/projects/<project_id>/files", methods=["GET", "POST"])
@login_required
def repo_files(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()

    repos = list_repos(org_name.organization_name, project_id, org_name.token)
    if repos[0] == False:
        flash(repos[1], "danger")
    return render_template("devops_projects/repos/files.html", org_id=org_id, project_id=project_id, repos=repos[1])

@app.route("/azure/devops/<org_id>/projects/<project_id>/repo/<repo_id>/files", methods=["GET", "POST"])
@login_required
def list_repo_files(org_id, project_id, repo_id):
    current_repo = request.args.get('repoName')
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    repo_files = list_repo_items(org_name.organization_name, project_id, repo_id,  org_name.token)
    if repo_files[0] == False:
        flash(repo_files[1], "danger")

    return render_template("devops_projects/repos/list_files.html", org_id=org_id, project_id=project_id, repo_files=repo_files[1], current_repo=current_repo,  token=org_name.token)


@app.route("/delete/<org_id>", methods=["POST"])
@login_required
def delete_org_by_id(org_id):
    try:
        AccessTokenSubmission.query.filter_by(id=org_id, user_id=current_user.id).delete()
        db.session.commit()  # type: ignore
        flash(f"ID: {org_id} Deleted!", "success")
    except:
        pass
    return redirect(url_for('dashboard'))


@app.route("/azure/devops/<org_id>/projects/<project_id>/workitems", methods=["GET", "POST"])
@login_required
def workitems(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    workitems = get_project_workitems(org_name.organization_name, project_id, org_name.token, work_item_type="Bug", state="New", assigned_to="")
    
    return render_template("devops_projects/boards/workitems.html", org_id=org_id, project_id=project_id, workitems=workitems[1])

@app.route("/azure/devops/<org_id>/projects/<project_id>/workitems/<work_item_id>", methods=["GET", "POST"])
@login_required
def workitem_details(org_id, project_id, work_item_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    workitem = get_work_item_by_id(org_name.organization_name, project_id, work_item_id, org_name.token)
    
    return render_template("devops_projects/boards/workitem_details.html", org_id=org_id, project_id=project_id, workitem=workitem)



@app.route("/azure/devops/<org_id>/projects/<project_id>/commits", methods=["GET", "POST"])
@login_required
def repo_commits(org_id, project_id):
    current_repo = request.args.get('repoName')

    return render_template("devops_projects/repos/commits.html", org_id=org_id, project_id=project_id)


@app.route('/azure/devops/<org_id>/projects/<project_id>/repos', methods=['GET'])
def list_repositories(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/git/repositories?api-version=6.0"
    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})

    if response.status_code == 200:
        repos = response.json().get('value', [])
        return jsonify([{'id': repo['id'], 'name': repo['name']} for repo in repos])
    else:
        return jsonify({'error': 'Failed to fetch repositories'}), response.status_code


@app.route('/azure/devops/<org_id>/projects/<project_id>/repos/commits', methods=['GET'])
def list_commits(org_id, project_id):

    repo_id = request.args.get('repoId')
    if not repo_id:
        return jsonify({'error': 'Repository ID is required'}), 400
    
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/git/repositories/{repo_id}/commits?api-version=6.0"

    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    if response.status_code == 200:
        commits = response.json().get('value', [])
        
        return jsonify([
            {
                'id': commit['commitId'],
                'message': commit['comment'],
                'author': commit['author']['name']
            } for commit in commits
        ])
    else:
        return jsonify({'error': 'Failed to fetch commits'}), response.status_code


@app.route('/azure/devops/<org_id>/projects/<project_id>/repos/commits/changes', methods=['GET'])
def get_commit_changes(org_id, project_id):
    commit_id = request.args.get('commitId')
    repo_id = request.args.get('repoId')
    if not commit_id or not repo_id:
        return jsonify({'error': 'Commit ID and Repository ID are required'}), 400

    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/git/repositories/{repo_id}/commits/{commit_id}/changes?api-version=6.0"
    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    if response.status_code == 200:
        changes = response.json()["changes"][0]["item"]
        
        code_data = requests.get(changes["url"], headers={"Authorization": f"{org_name.token}"})
        file_name = changes["path"]
        return jsonify({'file_path':file_name, 'changes': code_data.text})
    else:
        return jsonify({'error': 'Failed to fetch commit changes'}), response.status_code


@app.route('/azure/devops/<org_id>/projects/<project_id>/branches', methods=['GET'])
def get_branches(org_id, project_id):
            
    return render_template("devops_projects/repos/branches.html",  org_id=org_id, project_id=project_id)

@app.route('/azure/devops/<org_id>/projects/<project_id>/repos/branches', methods=['GET'])
def list_repo_branches(org_id, project_id):
    repo_id = request.args.get('repoId')

    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/git/repositories/{repo_id}/refs?api-version=6.0"
    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    if response.status_code == 200:
        branches = response.json()
        
        return jsonify(branches)
    else:
        return jsonify({'error': 'Failed to fetch commit changes'}), response.status_code



@app.route('/azure/devops/<org_id>/projects/<project_id>/pipelines', methods=['GET'])
def get_pipeline(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/pipelines?api-version=6.0"
    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    if response.status_code == 200:
        pipelines = response.json()
    else:
        pipelines = {}    

    return render_template("devops_projects/pipelines/pipeline.html",  org_id=org_id, project_id=project_id, pipelines=pipelines["value"])


@app.route('/azure/devops/<org_id>/projects/<project_id>/pipelines/list', methods=['GET'])
def list_pipelines(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/pipelines?api-version=6.0"
    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    if response.status_code == 200:
        pipelines = response.json()
        return jsonify(pipelines)
    else:
        return jsonify({'error': 'Failed to fetch commit changes'}), response.status_code

@app.route('/azure/devops/<org_id>/projects/<project_id>/pipelines/getyaml', methods=['GET'])
def get_pipeline_yaml(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    ID = request.args.get('id')
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apps/hub/ms.vss-build-web.ci-designer-hub?pipelineId={ID}&__rt=fps&__ver=2"

    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    if response.status_code == 200:
        pipelines = response.json()
        content = pipelines["fps"]["dataProviders"]["data"]["ms.vss-build-web.pipeline-editor-data-provider"]
        return jsonify(content)
    else:
        return jsonify({'error': 'Failed to fetch commit changes'}), response.status_code


@app.route('/azure/devops/<org_id>/projects/<project_id>/pipelines/library', methods=['GET'])
def get_pipeline_library(org_id, project_id):
    org_name = AccessTokenSubmission.query.filter_by(organization_name=org_id, user_id=current_user.id).first()
    url = f"https://dev.azure.com/{org_id}/{project_id}/_apis/distributedtask/variablegroups?api-version=7.1"
    response = requests.get(url, headers={"Authorization": f"{org_name.token}"})
    
    if response.status_code == 200:
        pipelines = response.json()  # Parse JSON response
    else:
        pipelines = {"count": 0, "value": []}  # Default in case of failure
    return render_template("devops_projects/pipelines/library.html",org_id=org_id, project_id=project_id, pipelines=pipelines)


@app.route("/signout", methods=["POST", "GET"])
def signout():
    logout_user()
    flash('Account Successfully Sign Out', 'success')
    return redirect(url_for('login'))

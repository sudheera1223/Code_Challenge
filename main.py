from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

GITHUB_API = "https://api.github.com"
BITBUCKET_API = "https://api.bitbucket.org/2.0"


def fetch_github_data(org_name):
    repos_url = f"{GITHUB_API}/orgs/{org_name}/repos"
    org_url = f"{GITHUB_API}/orgs/{org_name}"

    repos = []
    languages_count = {}
    topics = set()
    original_count = fork_count = 0

    # Paginate through repos
    while repos_url:
        response = requests.get(repos_url)
        if response.status_code != 200:
            break
        data = response.json()
        repos.extend(data)
        repos_url = response.links.get('next', {}).get('url')

    for repo in repos:
        if repo.get('fork'):
            fork_count += 1
        else:
            original_count += 1

        # Get languages
        lang_resp = requests.get(repo['languages_url'])
        if lang_resp.status_code == 200:
            langs = lang_resp.json()
            for lang in langs:
                languages_count[lang] = languages_count.get(lang, 0) + 1

        # Get topics
        if 'topics' in repo:
            for topic in repo['topics']:
                topics.add(topic)

    # Get followers
    followers_resp = requests.get(org_url)
    followers = 0
    if followers_resp.status_code == 200:
        followers = followers_resp.json().get('followers', 0)

    return {
        'original_repos': original_count,
        'forked_repos': fork_count,
        'followers': followers,
        'languages': languages_count,
        'topics': list(topics)
    }


def fetch_bitbucket_data(team_name):
    repos_url = f"{BITBUCKET_API}/repositories/{team_name}"
    team_url = f"{BITBUCKET_API}/teams/{team_name}"

    repos = []
    languages_count = {}
    original_count = fork_count = 0

    # Paginate through repos
    while repos_url:
        response = requests.get(repos_url)
        if response.status_code != 200:
            break
        data = response.json()
        repos.extend(data.get('values', []))
        repos_url = data.get('next')

    for repo in repos:
        if repo.get('parent'):
            fork_count += 1
        else:
            original_count += 1

        # Language (Bitbucket has limited support)
        lang = repo.get('language')
        if lang:
            languages_count[lang] = languages_count.get(lang, 0) + 1

    # Followers (Bitbucket may not expose follower counts the same way)
    followers_resp = requests.get(team_url)
    followers = 0
    if followers_resp.status_code == 200:
        followers = followers_resp.json().get('followers', 0)

    return {
        'original_repos': original_count,
        'forked_repos': fork_count,
        'followers': followers,
        'languages': languages_count
    }


@app.route('/api/merged-profile', methods=['GET'])
def merged_profile():
    github_org = request.args.get('github_org')
    bitbucket_team = request.args.get('bitbucket_team')

    if not github_org or not bitbucket_team:
        return jsonify({'error': 'Both github_org and bitbucket_team are required.'}), 400

    github_data = fetch_github_data(github_org)
    bitbucket_data = fetch_bitbucket_data(bitbucket_team)

    # Merge language counts
    merged_languages = github_data['languages']
    for lang, count in bitbucket_data['languages'].items():
        merged_languages[lang] = merged_languages.get(lang, 0) + count

    # Combine topics (Bitbucket doesn’t provide topics)
    merged_topics = github_data['topics']

    result = {
        'organization': github_org,
        'total_public_repos': {
            'github': {
                'original': github_data['original_repos'],
                'forks': github_data['forked_repos']
            },
            'bitbucket': {
                'original': bitbucket_data['original_repos'],
                'forks': bitbucket_data['forked_repos']
            }
        },
        'total_followers': {
            'github': github_data['followers'],
            'bitbucket': bitbucket_data['followers']
        },
        'languages': merged_languages,
        'repo_topics': merged_topics
    }

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)

"""
TODOs for production-ready code:
- Add caching to reduce API calls.
- Handle API rate limits and retries.
- Add authentication (GitHub/Bitbucket tokens).
- Write unit tests for fetch_github_data() and fetch_bitbucket_data().
- Add OpenAPI (Swagger) docs.
"""

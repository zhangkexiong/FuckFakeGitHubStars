import requests
import json
import queue

GITHUB_API_URL = 'https://api.github.com/graphql'
TOKEN = ''


def load_token():
    global TOKEN
    with open('token', 'r') as f:
        TOKEN = f.readline()


def run_query(query):
    request = requests.post(GITHUB_API_URL, json={'query': query}, headers={'Authorization': TOKEN})

    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))


REPOSITORY_STARGAZERS = {}
USER_STAR_REPOSITORIES = {}
NODE_ID_CONTENT = {}


def get_user_stars(node_id):

    if node_id not in NODE_ID_CONTENT:
        get_node_content(node_id)

    node_content = NODE_ID_CONTENT[node_id]
    if 'login' not in node_content:
        return None

    if node_id in USER_STAR_REPOSITORIES:
        return USER_STAR_REPOSITORIES[node_id]

    next_cursor = ''
    has_next = True
    all_star_repos = []

    def fetch_id_from_edge(edge):
        node = edge['node']
        NODE_ID_CONTENT[node['id']] = {'owner': node['owner']['login'],
                                       'name': node['name']}
        return node['id']

    while has_next:
        query_ql = '''
                query {
                  user(login: \"''' + node_content['login'] + '''\") {
                    starredRepositories(first: 100''' + next_cursor + ''') {
                      edges {
                        node {
                          id
                          owner {
                            login
                          }
                          name
                        }
                      }
                      pageInfo {
                        endCursor
                        hasNextPage
                      }
                    }
                  }
                }
                '''
        response = run_query(query_ql)
        if response is not None:
            repos = response['data']['user']['starredRepositories']
            edges = repos['edges']
            nodes = list(map(fetch_id_from_edge, edges))
            all_star_repos += nodes
            page_info = repos['pageInfo']
            next_cursor = ', after: \"' + page_info['endCursor'] + '\"'
            has_next = page_info['hasNextPage']

    USER_STAR_REPOSITORIES[node_id] = all_star_repos
    save_data()
    return all_star_repos


def get_repo_stargazers(node_id):

    if node_id not in NODE_ID_CONTENT:
        get_node_content(node_id)

    node_content = NODE_ID_CONTENT[node_id]
    if 'owner' not in node_content:
        return None

    if node_id in REPOSITORY_STARGAZERS:
        return REPOSITORY_STARGAZERS[node_id]

    next_cursor = ''
    has_next = True
    all_stargazers = []

    def fetch_id_from_edge(edge):
        node = edge['node']
        NODE_ID_CONTENT[node['id']] = {'login': node['login']}
        return node['id']

    while has_next:
        query_ql = '''
            query {
              repository(owner: \"''' + node_content['owner'] + '''\", name: \"''' + node_content['name'] + '''\") {
                stargazers(first: 100''' + next_cursor + ''') {
                  edges {
                    node {
                      id
                      login
                    }
                  }
                  pageInfo {
                    endCursor
                    hasNextPage
                  }
                }
              }
            }
            '''
        response = run_query(query_ql)
        if response is not None:
            stargazers = response['data']['repository']['stargazers']
            edges = stargazers['edges']
            nodes = list(map(fetch_id_from_edge, edges))
            all_stargazers += nodes
            page_info = stargazers['pageInfo']
            next_cursor = ', after: \"' + page_info['endCursor'] + '\"'
            has_next = page_info['hasNextPage']

    REPOSITORY_STARGAZERS[node_id] = all_stargazers
    save_data()
    return all_stargazers


def get_node_content(node_id):
    query_ql = '''
        query {
          node(id: \"''' + node_id + '''\") {
            ... on Repository {
              owner {
                login
              }
              name
            }
            ... on User {
              login
            }
          }
        }
        '''
    response = run_query(query_ql)
    node = response['data']['node']
    if 'owner' in node and 'name' in node:
        NODE_ID_CONTENT[node_id] = {'owner': node['owner']['login'],
                                    'name': node['name']}
    elif 'login' in node:
        NODE_ID_CONTENT[node_id] = {'login': node['login']}


def bfs_users_star_repos(node_id, max_level):
    visited = [node_id]
    q = queue.Queue()
    q.put(node_id)
    level = 1
    current_level_node_count_left = 1
    next_level_node_count = 0
    while not q.empty():
        current_node = q.get()
        print('bfs current level:' + format(level) + ' current node:' + current_node)
        current_level_node_count_left -= 1
        if current_level_node_count_left == 0:
            level += 1
            current_level_node_count_left = next_level_node_count
            next_level_node_count = 0
            if level > max_level:
                return
        result = get_user_stars(current_node)
        if result is None:
            result = get_repo_stargazers(current_node)
        if result is not None:
            for sub_node_id in result:
                if sub_node_id not in visited:
                    visited.append(sub_node_id)
                    q.put(sub_node_id)
                    next_level_node_count += 1


def save_data():
    with open('REPOSITORY_STARGAZERS.json', 'w') as f:
        json.dump(REPOSITORY_STARGAZERS, f)
    with open('USER_STAR_REPOSITORIES.json', 'w') as f:
        json.dump(USER_STAR_REPOSITORIES, f)
    with open('NODE_ID_CONTENT.json', 'w') as f:
        json.dump(NODE_ID_CONTENT, f)


def load_data():
    global REPOSITORY_STARGAZERS
    global USER_STAR_REPOSITORIES
    global NODE_ID_CONTENT
    with open('REPOSITORY_STARGAZERS.json', 'r') as f:
        REPOSITORY_STARGAZERS = json.load(f)
    with open('USER_STAR_REPOSITORIES.json', 'r') as f:
        USER_STAR_REPOSITORIES = json.load(f)
    with open('NODE_ID_CONTENT.json', 'r') as f:
        NODE_ID_CONTENT = json.load(f)


if __name__ == '__main__':
    load_token()
    load_data()
    bfs_users_star_repos('MDEwOlJlcG9zaXRvcnkxMTc1MTM4NTI=', 3)
    save_data()
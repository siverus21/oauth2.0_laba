from flask import Flask, redirect, request, session, url_for, render_template
import requests
import os
from dotenv import load_dotenv

# Загрузить переменные из .env файла
load_dotenv()

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Клиентские данные для VK
VK_CLIENT_ID = os.getenv('VK_CLIENT_ID')
VK_CLIENT_SECRET = os.getenv('VK_CLIENT_SECRET')
VK_REDIRECT_URI = os.getenv('VK_REDIRECT_URI')

# Клиентские данные для GitHub
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI')


# Главная страница
@app.route('/')
def index():
    # Проверяем, есть ли токены для VK и GitHub в сессии
    vk_logged_in = 'vk_token' in session
    github_logged_in = 'github_token' in session

    return render_template('index.html', vk_logged_in=vk_logged_in, github_logged_in=github_logged_in)


# ==================== VK OAuth 2.0 ====================
@app.route('/vk/login')
def vk_login():
    if 'vk_token' in session:
        return redirect(url_for('vk_callback'))

    vk_auth_url = (
        'https://oauth.vk.com/authorize?client_id={}&redirect_uri={}&response_type=code'
        '&scope=email&display=page'
    ).format(VK_CLIENT_ID, VK_REDIRECT_URI)
    return redirect(vk_auth_url)


@app.route('/vk/callback/')
def vk_callback():
    if 'vk_token' in session:
        access_token = session['vk_token']
        user_info = requests.get('https://api.vk.com/method/users.get', params={
            'access_token': access_token,
            'v': '5.199'
        }).json()

        profile_info = requests.get('https://api.vk.com/method/account.getProfileInfo', params={
            'access_token': access_token,
            'v': '5.199'
        }).json()

        user_name = user_info['response'][0]['first_name'] + ' ' + user_info['response'][0]['last_name']

        profile_data = {
            'ID': profile_info['response'].get('id', 'Не указано'),
            'Дата рождения': profile_info['response'].get('bdate', 'Не указано'),
            'Имя': profile_info['response'].get('first_name', 'Не указано'),
            'Фамилия': profile_info['response'].get('last_name', 'Не указано')
        }

        return render_template('vk_callback.html', user_name=user_name, profile_data=profile_data)

    code = request.args.get('code')
    token_url = 'https://oauth.vk.com/access_token'
    payload = {
        'client_id': VK_CLIENT_ID,
        'client_secret': VK_CLIENT_SECRET,
        'redirect_uri': VK_REDIRECT_URI,
        'code': code
    }
    response = requests.get(token_url, params=payload)
    vk_data = response.json()

    # Сохраняем токен и информацию в сессии
    session['vk_token'] = vk_data['access_token']
    return redirect(url_for('vk_callback'))


@app.route('/vk/logout')
def vk_logout():
    # Удаляем токен из сессии
    session.pop('vk_token', None)
    return redirect(url_for('index'))


# ==================== GitHub OAuth 2.0 ====================
@app.route('/github/login')
def github_login():
    if 'github_token' in session:
        return redirect(url_for('github_callback'))

    github_auth_url = (
        'https://github.com/login/oauth/authorize?client_id={}&redirect_uri={}&scope=user'
    ).format(GITHUB_CLIENT_ID, GITHUB_REDIRECT_URI)
    return redirect(github_auth_url)


@app.route('/github/callback/')
def github_callback():
    if 'github_token' in session:
        access_token = session['github_token']
        user_info = requests.get('https://api.github.com/user', headers={
            'Authorization': f'token {access_token}'
        }).json()

        return render_template('github_callback.html', user_info=user_info)

    code = request.args.get('code')
    token_url = 'https://github.com/login/oauth/access_token'
    headers = {'Accept': 'application/json'}
    payload = {
        'client_id': GITHUB_CLIENT_ID,
        'client_secret': GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': GITHUB_REDIRECT_URI
    }
    try:
        response = requests.post(token_url, headers=headers, data=payload, timeout=10)
        github_data = response.json()

        if 'error' in github_data:
            return f"Error: {github_data.get('error_description', 'Unknown error')}"

        access_token = github_data.get('access_token')
        if not access_token:
            return "Error: No access token received"

        # Сохраняем токен и информацию в сессии
        session['github_token'] = access_token
        return redirect(url_for('github_callback'))
    except requests.exceptions.RequestException as e:
        return f"Request failed: {e}"


@app.route('/github/logout')
def github_logout():
    # Удаляем токен из сессии
    session.pop('github_token', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=5000, debug=True)

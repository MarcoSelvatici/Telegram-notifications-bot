import telegram
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
import time
import threading

token = ''
bot = telegram.Bot(token=token)
saved_users = []
users_dict = {} # made of Users

interval = 30.0 # interval in seconds between checking for updates

class User:
    flags = {'register': False}
    fb_username = ''
    fb_password = ''
    insta_username = ''
    insta_password = ''
    last_insta = False # last notifications
    last_fb = [0, 0, 0] # last notifications
    chatid = None

def clear_memory(user):
    user.flags['register'] = False

def get_name(update):
    first_name = update['message']['chat']['first_name']
    last_name = update['message']['chat']['last_name']
    return str(first_name+'_'+last_name)

def register_new_user(update):
    name = get_name(update)
    if name in saved_users:
        return
    saved_users.append(name)
    users_dict[name] = User
    users_dict[name].chatid = update.message['chat']['id']
    print("New user:", name)

def instagram_notifications(user):
    driver = webdriver.PhantomJS(executable_path='yourPathTo/phantomjs-2.1.1-windows/bin/phantomjs.exe')
    url = 'https://www.instagram.com/'
    driver.get(url)
    driver.find_element_by_class_name('_fcn8k').click()  # already got an account
    driver.find_element_by_name('username').send_keys(user.insta_username)  # username
    driver.find_element_by_name('password').send_keys(user.insta_password)  # password
    driver.find_element_by_css_selector('._ah57t._84y62._i46jh._rmr7s').click()  # login
    #time.sleep(2)  # wait for the login
    try: # try to login
        WebDriverWait(driver, timeout=5).until(presence_of_element_located((By.ID, 'mainFeed')))  # wait until the instagram home is loaded (timeout 5s)
    except:
        print('Error in instagram login for:', user.insta_username)
        return

    new_notifications = True
    try: # check for notifications
        driver.find_element_by_css_selector('._im3et._vbtk2.coreSpriteDesktopNavActivity._l0mgk')  # only if there are new notifications
    except:
        #bot.sendMessage(chat_id=user.chatid, parse_mode='Markdown', text='*Instagram*\nNo notifications')
        print('Nothing new on instagram for', user.insta_username)
        new_notifications = False
        user.last_insta = False

    if new_notifications and user.last_insta is False:
        user.last_insta = True
        print('New notifications on instagram for', user.insta_username)
        bot.sendMessage(chat_id=user.chatid, parse_mode='Markdown', text='*Instagram*\nNew notifications, please check from https://www.instagram.com/')
    driver.quit()

def facebook_notifications(user):
    driver = webdriver.PhantomJS(executable_path='yourPathTo/phantomjs-2.1.1-windows/bin/phantomjs.exe')
    url = 'https://www.facebook.com/'
    driver.get(url)
    # print('logging in...')
    driver.find_element_by_name('email').send_keys(user.fb_username)
    driver.find_element_by_name('pass').send_keys(user.fb_password)
    driver.find_element_by_name('login').click()
    try:  # try to login
        WebDriverWait(driver, timeout=5).until(presence_of_element_located((By.CSS_SELECTOR, '._52jj._5u5a._5v_i')))  # wait until the instagram home is loaded (timeout 5s)
    except:
        print('Error in facebook login for:', user.fb_username)
        return
    # print("'non ora' page")
    driver.find_element_by_css_selector('._52jh._54k8._56bs._56b_._56bw._56bt').click()  # 'non ora' button
    # check notifications
    print("\n Facebook:", user.fb_username)
    notification_icon = driver.find_element_by_id('notifications_jewel')  # notifications
    notifications = int(notification_icon.find_element_by_class_name('_59tg').get_attribute('innerHTML'))
    print(notifications, 'new notifications')
    requests_icon = driver.find_element_by_id('requests_jewel')  # friend requests
    requests = int(requests_icon.find_element_by_class_name('_59tg').get_attribute('innerHTML'))
    print(requests, 'new friend requests')
    messages_icon = driver.find_element_by_id('messages_jewel')  # messages
    messages = int(messages_icon.find_element_by_class_name('_59tg').get_attribute('innerHTML'))
    print(messages, 'new messages')

    curr = [notifications, requests, messages]

    if messages or requests or notifications and curr != user.last_fb:
        text = str(notifications) + ' new notifications\n' + str(requests) + ' new friend requests\n' + str(messages) + ' new messages\nPlease check from https://www.facebook.com/'
        bot.sendMessage(chat_id=user.chatid, parse_mode='Markdown', text=('*Facebook*\n' + text))

    user.last_fb = [notifications, requests, messages]

def start_instagram_update_thread(user):
    print('insta_thread')
    threading.Timer(interval, start_instagram_update_thread, [user]).start() # start a new thread for the user
    instagram_notifications(user)

def start_facebook_update_thread(user):
    print('facebook_thread')
    threading.Timer(interval, start_facebook_update_thread, [user]).start() # start a new thread for the user
    facebook_notifications(user)

def start_threads(user):
    print('starting threads...')
    #start_instagram_update_thread(user)
    time.sleep(interval/2)
    start_facebook_update_thread(user)

def reply(update):
    #print(update)
    name = get_name(update)
    if name in saved_users:
        user = users_dict[name]
    text = update.message.text
    #print(text)
    if text == '/start':
        register_new_user(update)
        user = users_dict[name]
        clear_memory(user)
        update.message.reply_text(parse_mode='Markdown', text="Hi! If you are not already registered please try the /register button!")
    elif text == '/register':
        update.message.reply_text(parse_mode='Markdown',
                                  text="Please write your *instagram* and *facebook* usernames and passwords like this:\n_instaUsername\ninstaPassword\nfacebookUername\nfacebookPassword_")
        user.flags['register'] = True
    elif user.flags['register']:
        user.insta_username, user.insta_password, user.fb_username, user.fb_password = update.message.text.split('\n')
        update.message.reply_text("Got it! I will try to login...")
        clear_memory(user)
        threading.Thread(target=start_threads, args=[user]).start() # open a thread to start threads, so i can sleep(interval/2) without blocking the code

def get_updates(bot, last_update_id):
    updates = []
    for update in bot.get_updates(offset=(last_update_id + 1), timeout=10):
        last_update_id = update.update_id
        updates.append(update)
    return updates, last_update_id

def main():
    last_update_id = 0
    while True:
        time.sleep(0.3)
        new_updates, last_update_id = get_updates(bot, last_update_id)
        for update in new_updates:
            #a = 3
            reply(update)

if __name__ == '__main__':
    main()

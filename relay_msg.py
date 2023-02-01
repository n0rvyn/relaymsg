#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyleft 2020-2023 by ZHANG ZHIJIE.
# All rights reserved.

# Last Modified Time: 31/01/21 10:23
# Author: ZHANG ZHIJIE
# Email: norvyn@norvyn.com
# File Name: relay_msg.py
# Tools: PyCharm

"""
Android Debug Bridge (ADB) Command Line Interface Python Module

v1.0.0 - 2023/02/01
    Read new message and take a screenshot, send the picture to Wechat
    todo Read msg as text, copy from app & send to Wechat
    todo Add log support

"""
import os
import subprocess
import time
import random
import platform
import pinyin
import sys

_ADB_HOME_ = '/opt/adb/' if platform.system() == 'Linux' else '/Users/beyan/Documents/Scripts/43-Android/adb/'
_TMP_DIR_ = '/tmp'

# define tmp xml file for adb ui dump
_TMP_XML_FILE_ = os.path.join(_TMP_DIR_, 'adb_ui_dump.xml')
_SCREENSHOT_FILE_ = os.path.join(_TMP_DIR_, f'adb_screenshot_{random.randint(1000, 9999)}.png')


# Only support fetching single android device ID & SN.
# todo support multiple devices
def fetch_device_SN(return_id=False) -> str:
    """
    return: android device serial number list

    9f11ca4d device usb:1-1.2 product:on7xltezc model:SM_G6100 device:on7xltechn transport_id:58
    """
    _command = f'{_ADB_HOME_}/adb devices -l'
    _output_list = subprocess.getoutput(_command).split('\n')

    _SN = _output_list[1].split(' ')[0]
    _ID = _output_list[1].split(':')[-1]

    return _ID if return_id else _SN


class AndroidConsole(object):
    """
    ADB Operate Console
    """

    def __init__(self,
                 device_sn: str = None,
                 app_name: str = None,
                 app_actv_name: str = None,
                 app_run_keyword: str = None):
        """
        app_run_keyword (str): keyword to identify app is running.
        """
        self.sn = device_sn
        self.name = app_name
        self.actv_name = app_actv_name
        self.run_keyword = app_run_keyword

        self.last_output = []

        self.tmp_file = _TMP_XML_FILE_
        self.screenshot_file_local = _SCREENSHOT_FILE_
        # the name of screenshot photo saved on the phone
        self.screenshot_file_phone = f'/sdcard/screen_{random.randint(1000, 9999)}.png'

        # the middle point of the phone screen
        self.screen_mid_point = self.fetch_mid_of_screen()

    # low level cli for internal using
    def _send_shell_command(self, command):
        """
        send shell command to android device connected

        return True/False, depends on if command is executed successfully.
        """
        # Light on the screen by sending key event 224
        os.system(f"""{_ADB_HOME_}/adb -s {self.sn} shell input keyevent 224""")

        # sending command to adb shell
        command = f"""{_ADB_HOME_}/adb -s {self.sn} {command}"""

        # fetching output of the command and storing to class attribute self.last_output
        # return True or False depends on the return code
        _output = subprocess.getstatusoutput(command)
        _return = _output[0]
        self.last_output = _output[1].split('\n')
        return True if _return == 0 else False

    def get_point_of_text(self, text: str = None, reverse_order: bool = True):
        """
        get touch point x,y value list of text on phone screen
        """
        command = f'exec-out uiautomator dump /dev/tty > {self.tmp_file}'
        self._send_shell_command(command)
        point = []

        try:
            with open(self.tmp_file, 'r+') as f:
                dump_txt = f.readlines()
                f.close()

        except FileNotFoundError as err:
            print(err, 'dump screen txt failed.')
            return point

        # ui_data = [_line for _line in self.last_output.split('/><')]
        # ui_data = [_line for _line in dump_txt[0].split('/><node')]
        ui_data = [_line for _line in dump_txt[0].split('><node')]

        if reverse_order:
            ui_data.reverse()  # for looking up the last saved pictures using Wechat

        try:
            for _line in ui_data:
                if text in _line:
                    for _part in _line.split():
                        if 'bounds=' in _part:
                            _part = _part.strip('bounds="[]').split('][')
                            point0 = _part[0].split(',')
                            point1 = _part[1].split(',')
                            point = [str((int(point0[0]) + int(point1[0])) // 2),
                                     str((int(point0[1]) + int(point1[1])) // 2)]
        except IndexError:
            pass
        return point

    def read_screen_text(self, label: str = None, sub_label: str = None, read_all: bool = True):
        """
        label (str) - the keyword only contains in the data block
        sub_label (str) - ...
        """
        label = '' if label is None else label
        sub_label = '' if sub_label is None else sub_label

        command = f'exec-out uiautomator dump /dev/tty > {self.tmp_file}'
        self._send_shell_command(command)

        text = ''

        try:
            with open(self.tmp_file, 'r+') as f:
                dump_txt = f.readlines()
                f.close()

        except FileNotFoundError as err:
            print(err, 'dump screen txt failed.')
            return text

        ui_data = [_line for _line in dump_txt[0].split('><node')]
        try:
            for _line in ui_data:
                if label in _line:
                    _sub_data_list = _line.split('"')
                    for _sub_line in _sub_data_list:
                        if sub_label in _sub_line:
                            _text_tmp = _sub_data_list[_sub_data_list.index(_sub_line) + 1]
                            if read_all:
                                text += _text_tmp + '\n'
                            else:
                                return _text_tmp
            return text

        except IndexError as err:
            raise err

    def launch_app(self):
        """
        launch application in phone
        """
        return self._send_shell_command(f'shell am start -n {self.actv_name}')

    def launch_app_monkey(self):
        return self._send_shell_command(f'shell monkey -p {self.name} 1')

    def shutdown_app(self):
        """
        shutdown application via actv_name
        """
        return self._send_shell_command(f'shell am force-stop {self.name}')

    def is_app_inst(self):
        """
        return true if application installed.
        """
        return self._send_shell_command(f'shell pm list packages | grep {self.name}')

    def is_app_launched(self):
        """
        return true if application is running
        """
        if self.get_point_of_text('text="权限申请"'):
            self.tap_screen(self.get_point_of_text('text="取消"'))
        return self.get_point_of_text(self.run_keyword)

    def return_back(self):
        """
        back to last page
        """
        return self._send_shell_command('shell input keyevent KEYCODE_BACK')

    def return_home(self):
        """
        back to home screen
        """
        return self._send_shell_command('shell input keyevent KEYCODE_HOME')

    def power_on(self):
        """
        tap power key
        """
        return self._send_shell_command('shell input keyevent POWER')

    def screen_off(self):
        """
        turn-off screen
        """
        return self._send_shell_command('shell input keyevent 223')

    def tap_screen(self, point: list):
        """
        touch the pointer on screen
        """
        return False if len(point) != 2 else self._send_shell_command(f'shell input tap {point[0]} {point[1]}')

    def paste_text(self):
        return self._send_shell_command('shell input keyevent 279')

    def copy_text(self, x: int, y: int):
        self._send_shell_command('shell input keyevent 278')

    def swipe_screen_up_down(self,
                             up: bool = True,
                             down: bool = False):
        """
        swipe up or down of the screen
        """
        from_x_point = self.screen_mid_point[0]
        from_y_point = self.screen_mid_point[-1]
        to_x_point = from_x_point
        try:
            from_y_point = int(from_y_point)
        except ValueError:
            pass

        # to_y_point = from_y_point // 2 + from_y_point if up else from_y_point // 2
        to_y_point = from_y_point // 2 if up else from_y_point // 2 + from_y_point

        return self._send_shell_command(
            f'shell input swipe {from_x_point} {str(from_y_point)} {to_x_point} {str(to_y_point)}')

    def take_screenshot(self):
        """
        take screenshot to local
        """
        if self._send_shell_command(f'shell screencap {self.screenshot_file_phone}'):
            return self._send_shell_command(f'pull {self.screenshot_file_phone} {self.screenshot_file_local}')
        else:
            return False

    def set_screen_on_secs(self, sec=1):
        """
        set the time of screen on
        """
        return self._send_shell_command(f'shell settings put system screen_off_timeout {str(int(sec * 59998))}')

    def wait_with_screen_on(self, times=1):
        """
        waiting while keeping screen on
        """
        count = 0
        times *= 2
        while True:
            count += 1
            self._send_shell_command('shell input keyevent 224')
            if count >= times:
                return True

    def fetch_mid_of_screen(self):
        """
        fetch middle point of screen
        """
        self._send_shell_command(f'shell wm size')
        wm_size = self.last_output[0].split(':')[-1].split('x')
        return [str(int(wm_size[0]) // 2), str(int(wm_size[1]) * 3 // 5)]

    def input_text(self, text: str):
        """
        Chinese not supported by ADB
        """
        text = pinyin.get(text, format='strip', delimiter='')
        text = text.replace(' ', '%s')  # sed 's/ /\%s/g'
        text = text.replace('[_<>|&$;()\"]', '\\&')
        # sed -e 's/[_<>|&$;()\"]/\/&/g' -e 's/!+/!/g')'

        input_cmd = f"""shell input text '{text}'"""
        return self._send_shell_command(input_cmd)


class Wechat(AndroidConsole):
    """
    Wechat operate console
    """

    def __init__(self, device_sn):
        app_name = 'com.tencent.mm'
        app_actv_name = 'com.tencent.mm/.ui.LauncherUI'
        app_run_keyword = '"通讯录"'
        AndroidConsole.__init__(self, device_sn, app_name, app_actv_name, app_run_keyword)

    def launch_wechat(self):
        return self.launch_app()

    def kill_wechat(self):
        return self.shutdown_app()

    def return_wechat_main_page(self):
        while not self.get_point_of_text('"通讯录"'):
            self.return_back()
        return self.tap_screen(self.get_point_of_text('"微信"'))

    def is_wechat_running(self):
        return self.is_app_launched()

    def chat_with_user(self,
                       user_profile_name: str,
                       select_input_box: bool = True,
                       try_times: int = 10,
                       send_msg_label: str = 'text="发消息"'):
        # make sure Wechat is running at foreground
        self.launch_wechat() if not self.is_wechat_running() else ''
        # ADB dump text
        user_profile_name = f'''"{user_profile_name}"'''

        # search user at current page
        user_point = self.get_point_of_text(user_profile_name)
        if not user_point:  # search user in 'contact' page
            self.return_wechat_main_page()
            self.tap_screen(self.get_point_of_text('通讯录'))
            count = 0

            while True:
                user_point = self.get_point_of_text(user_profile_name)
                if user_point or count >= try_times:
                    break
                else:
                    self.swipe_screen_up_down()
                    count += 1
        if not user_point:
            raise f'User [{user_profile_name} not found error.]'
        else:
            self.tap_screen(user_point)
            _return = self.tap_screen(self.get_point_of_text(send_msg_label))
            if select_input_box:
                return self.tap_screen(self.get_point_of_text('android.widget.EditText'))
            else:
                return _return

    def send_last_pic(self, user_profile_name: str, try_times: int = 10):
        self.chat_with_user(user_profile_name, select_input_box=False)

        print(f'Try send last picture to user {user_profile_name}')
        self.tap_screen(self.get_point_of_text('content-desc="更多功能按钮'))
        self.tap_screen(self.get_point_of_text('text="相册"'))
        self.tap_screen(self.get_point_of_text('text="去授权"'))
        self.tap_screen(self.get_point_of_text('text="总是允许"'))
        self.tap_screen(self.get_point_of_text('text="原图"'))
        self.tap_screen(self.get_point_of_text('class="android.widget.CheckBox"'))

        count = 0
        while not self.tap_screen(self.get_point_of_text('text="发送')):
            self.wait_with_screen_on(2)
            if count >= try_times:
                return False

        return self.get_point_of_text('"切换到按住说话"')

    def send_msg(self, user_profile_name: str, msg: str = None):
        self.chat_with_user(user_profile_name)

        self.input_text(msg)
        # todo find out point of 'input box' and tap
        # todo send adb key event 279, paste message
        # try ADB_INPUT_TEXT
        # 'https://stackoverflow.com/questions/14224549/adb-shell-input-unicode-character/23482717'
        self.wait_with_screen_on()
        self.tap_screen(self.get_point_of_text('text="发送"'))
        if self.get_point_of_text('text="发送"'):
            self.tap_screen(self.get_point_of_text('text="发送"'))
        print('Done')


class DingTalk(AndroidConsole):
    """
    Once used for automatically checking in.
    Lots of mistakes, fixed soon or never...
    """

    def __init__(self, devID, coName, waitSecs=random.randint(60, 600)):
        self.devID = devID
        self.coName = coName
        self.appName = 'com.alibaba.android.rimet'
        self.appActvName = 'com.alibaba.android.rimet/.biz.LaunchHomeActivity'
        self.waitSecs = waitSecs
        AndroidConsole.__init__(self, self.devID, self.appName, self.appActvName)

    def getCurrentCompany(self):
        """
        """
        cmdStr = 'exec-out uiautomator dump /dev/tty > ' + self.tmpFile
        if not self.sendCommand(cmdStr):
            return ''
        uiData = ''
        try:
            with open(self.tmpFile, 'r') as f:
                uiData += f.readline()
            f.close()
        except FileNotFoundError:
            print('Temp File Not Found.')
            return ''
        os.system('rm -rf ' + self.tmpFile)
        for line in uiData.split('<'):
            keyword = 'com.alibaba.android.rimet:id/menu_current_company'
            keyword = 'com.alibaba.android.rimet:id/tv_org_name'
            if keyword in line:
                for statement in line.split():
                    if 'text' in statement:
                        return statement.strip().split('"')[-2]
        return ''

    def changeCurrCo(self, currCoName, toCoName):
        """
        """
        if not currCoName or not toCoName:
            return False
        try:
            self.tapScreen(self.getIconOrTextPointer(currCoName))
        except ValueError:
            return False
        try:
            self.tapScreen(self.getIconOrTextPointer(toCoName))
        except ValueError:
            return False
        # add method to verify if changed successfully.
        if self.getCurrentCompany() == toCoName:
            return True
        else:
            return False

    def getWorkConsoleIcon(self):
        """
        """
        xPointer = ''
        yPointer = ''
        try:
            leftPointer = self.getIconOrTextPointer('"协作"')
            rightPointer = self.getIconOrTextPointer('"通讯录"')
            yPointer = leftPointer[1]
            xPointer = str((int(rightPointer[0]) - int(leftPointer[0])) // 2 + int(leftPointer[0]))
        except IndexError:
            return []
        pointer = [xPointer, yPointer]
        return pointer

    def launchDingDing(self):
        """
        """
        return self.launchApp()

    def isDingDingRunning(self):
        """
        """
        return self.isAppLaunched()

    def shutdownDingDing(self):
        """
        """
        return self.shutdownApp()

    def checkIn(self, wechatUser):
        """
        """
        print('-' * 20 + 'Check in start' + '-' * 20)
        # os.system('date "+%y/%m/%d %H:%M:%S" | ' + "awk '{print \"Started at: \"$1\" \"$2}'")
        print('Started at: ', time.strftime('%Y/%m/%d %A %H:%M:%S'))
        screen_off_time = 1800
        print('Set system screen off timeout {}s: '.format(screen_off_time), end='', flush=True)
        if self.setScreenOnSecs(1800):
            print('Passed')
        else:
            print('Failed')

        print('Check Android devices list: ', end='', flush=True)
        # if sendCommand('devices -l | grep -v "List of devices attached" | grep -v "^$" &>/dev/null'):
        if self.sendCommand('devices -l | grep "{}" &>/dev/null'.format(self.devID)):
            print('Passed')
        else:
            print('Failed, connect Android device to this computer.')
            return False

        print('Generate random seconds for waiting: ', end='', flush=True)
        print(str(self.waitSecs) + 's')
        time.sleep(self.waitSecs)

        print('Shutdown DingTalk: ', end='', flush=True)
        self.shutdownDingDing()
        self.shutdownDingDing()
        while True:
            if self.isDingDingRunning():
                self.shutdownDingDing()
                self.lightOnScreenAndWait(1)
            else:
                print('Passed')
                break

        print('Launch DingTalk: ', end='', flush=True)
        self.launchDingDing()
        self.lightOnScreenAndWait(3)
        while True:
            if self.isDingDingRunning():
                print('Passed')
                break
            else:
                self.lightOnScreenAndWait(1)
                self.launchDingDing()

                # modify
        print('Tap work console icon: ', end='', flush=True)
        # tapScreen(getIconOrTextPointer('工作台'))
        # tapScreen(getIconOrTextPointer('home_bottom_tab_text'))
        self.tapScreen(self.getWorkConsoleIcon())
        while True:
            currentCoName = self.getCurrentCompany()
            if currentCoName:
                print('Passed')
                break
            else:
                self.lightOnScreenAndWait()
                self.tapScreen(self.getWorkConsoleIcon())

        print('Verify if the current company is {}: '.format(self.coName), end='', flush=True)
        if currentCoName == self.coName:
            print('Passed')
        else:
            print('Failed')
            print('Change to company {}: '.format(self.coName), end='', flush=True)
            while True:
                if self.changeCurrCo(currentCoName, self.coName):
                    print('Passed')
                    break
                else:
                    self.lightOnScreenAndWait(1)

        print('Press checkin icon: ', end='', flush=True)
        while True:
            checkInIcon = self.getIconOrTextPointer('"考勤打卡"')
            if not checkInIcon:
                self.lightOnScreenAndWait(1)
            else:
                if checkInIcon[1] <= '194':
                    self.swapDownQuarterScreen()
                    checkInIcon = self.getIconOrTextPointer('考勤打卡')

                elif checkInIcon[1] >= '1700':
                    self.swapUpQuarterScreen()
                    checkInIcon = self.getIconOrTextPointer('考勤打卡')

                self.tapScreen(checkInIcon)
                print('Passed')
                break

        # add method to verify if the big icon is exit.
        print('Verify if the current page is the one we wanted: ', end='', flush=True)
        # This page return 'ERROR: could not get idle state.'
        count = 0
        while True:
            if count > 10:
                print('Failed, check in anyway!')
                break
            if not self.getIconOrTextPointer(self.coName):
                print('Passed')
                break
            else:
                self.lightOnScreenAndWait(1)
                count += 1

        print('Finally, check in: ', end='', flush=True)
        self.tapScreen(self.midPoint)
        self.lightOnScreenAndWait(1)
        self.tapScreen(self.midPoint)
        self.lightOnScreenAndWait(1)

        # continueIcon = ['818', '1114']
        continueIcon = self.getIconOrTextPointer('text="继续打卡"')
        if continueIcon:
            continueIcon = self.getIconOrTextPointer('text="继续打卡"')
            print('ORG changed before, continue check in.')
            self.tapScreen(continueIcon)
            self.lightOnScreenAndWait(1)
            self.tapScreen(continueIcon)
        else:
            print('Passed')

        print('Take screenshot & return home screen: ', end='', flush=True)
        self.lightOnScreenAndWait(1)
        self.screenShot()
        self.lightOnScreenAndWait(1)
        if self.returnHome():
            print('Passed')
        else:
            print('Failed')

        sendMail(self.coName, subject='通知：{}打卡记录自动发送'.format(self.coName), image=self.screenShotLocalFile)
        wechatCon = wechatConsole(self.devID)
        coNameEng = pinyin.get(self.coName, format='strip', delimiter='')
        # Capitalize the first letter of the string
        coNameEng = coNameEng.replace(coNameEng[0], coNameEng[0].upper(), 1)
        wechatCon.sendMsg2one(wechatUser, '{} checked in at: {}.'
                              .format(coNameEng, time.strftime("%m/%d %a %H:%M")), lastPic=True)
        self.returnHome()
        self.screenOff()
        print('-' * 20 + 'Check in done' + '-' * 20)

    def OneKeyClean(self):
        """
        """
        pass


class Message(AndroidConsole):
    def __init__(self, device_sn):
        app_name = 'com.samsung.android.messaging'
        app_actv_name = 'com.samsung.android.messaging/com.android.mms.ui.ConversationComposer'
        app_run_keyword = '"对话"'
        AndroidConsole.__init__(self, device_sn, app_name, app_actv_name, app_run_keyword)

    def launch_msg(self):
        print('Shutdown Message App for restarting: ', self.shutdown_app())
        print('Launch Message App: ', self.launch_app_monkey())

    def read_msg(self, label: str = None, sub_label: str = None):
        label = 'com.samsung.android.messaging:id/base_list_item_data' if not label else label
        sub_label = 'content-desc' if not sub_label else sub_label
        return self.read_screen_text(label, sub_label)

    def read_new_msg(self, new_msg_label: str = None):
        new_msg_label = '条未读信息' if not new_msg_label else new_msg_label
        new_msgs = ''
        # todo tap screen to the bottom, read the last unread new.

        _point = self.get_point_of_text(new_msg_label)
        # read message only if 'new_msg_label' exist
        while _point:
            self.tap_screen(_point)
            _point = None

            """
            _inter_point = self.get_point_of_text(new_msg_label)
            if _inter_point:
                self.tap_screen(_inter_point)
                new_msgs += self.read_msg() + '\n'
            """
            new_msgs += self.read_msg() + '\n'
            _point = self.get_point_of_text(new_msg_label)

        _prompt = 'New messages fetched.' if new_msgs else 'All messages has been read.'
        print(_prompt)
        return new_msgs

    def read_new_msg_as_screenshot(self, new_msg_label: str = None):
        new_msg_label = '条未读信息' if not new_msg_label else new_msg_label
        # todo tap screen to the bottom, read the last unread new.
        _point = self.get_point_of_text(new_msg_label)
        # read message only if 'new_msg_label' exist
        if _point:
            self.tap_screen(_point)
            print('Reading 1 new message to screenshot...')
            return self.take_screenshot()
        else:
            print('All messages been read.')
            return False

    def read_msg_from(self, sender: str):
        msg_entry_label = '''"通知类信息"'''

        _point = self.get_point_of_text(msg_entry_label)
        # read message only if 'new_msg_label' exist
        if _point:
            self.tap_screen(_point)

            _sender_point = self.get_point_of_text(sender)
            _count = 0
            while not _sender_point and _count <= 10:
                self.swipe_screen_up_down()
                _sender_point = self.get_point_of_text(sender)
                _count += 1

            if _sender_point:
                self.tap_screen(_sender_point)
                return self.read_msg()
            else:
                print('No sender found.')
                return None
        else:
            print('sys error.')
            return None


def relay_msg_to_wechat(wechat_user: str):
    sn = fetch_device_SN()

    msg_app = Message(sn)
    msg_app.launch_msg()
    # messages = msg_app.read_new_msg()

    # print(msg.read_msg_from('10086'))
    wechat = Wechat(sn)
    while msg_app.read_new_msg_as_screenshot():
        wechat.send_last_pic(wechat_user)

    wechat.return_back()
    wechat.screen_off()


if __name__ == '__main__':
    relay_msg_to_wechat(sys.argv[1])




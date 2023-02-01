# relaymsg

---
Read new messages from Android, take a screenshot, send the picture to Wechat user.

#### Necessary Packages

---
- subprocess
- pinyin (Chinese not supported by ADB, messages must be transformed to Pinyin)

#### Usage

---

```bash
python3 /path/to/relay_msg.py wechat_user
```
or
```bash
crontab -e

*/5 * * * *   /path/to/relay_msg.py USER >> /var/log/relaymsg.log 2>&1
```

#### Author

---

[Website](https://norvyn.com)

norvyn@norvyn.com

#### Tested

---
- Python3.11
- Gentoo Linux 2.9
- Galaxy On7(2016)
- Android 8.0.0




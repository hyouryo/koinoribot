# KoinoriBot（维护版）
![Python Version](https://img.shields.io/badge/python-3.8+-blue)
[![试用群](https://img.shields.io/badge/试用/一群-冰祈杂谈总铺-brightgreen)](https://jq.qq.com/?_wv=1027&k=o3WzKAfn)
[![试用群](https://img.shields.io/badge/试用/二群-冰祈杂谈分铺-brightgreen)](https://jq.qq.com/?_wv=1027&k=fdFbP60u)


## KoinoriBot是什么？
 - KoinoriBot是Hoshinobot的一款插件，提供了很多好玩的功能，包括但不限于钓鱼，炒股，宠物
 - 是居家旅行必备的群内活跃气氛的小插件


## 部署方法
- 安装python3.8.0
```
由于过于老旧所以我也不知道怎么装捏
```

- KoinoriBot是一款插件，所以我们需要先安装Hoshinobot
```sh
git clone https://github.com/Ice9Coffee/HoshinoBot.git
```
- 建立虚拟环境
```sh
cd Hoshinobot
python3.8 -m venv venv 
source venv/bin/activate
```

- 更换成国内镜像源（不做也行……但下载速度……你懂的）
```sh
pip3.8 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```
- 将KoinoriBot放置在hoshino/modules下
```sh
cd hoshino/modules
git clone https://github.com/CGangel/koinoribot.git
```
- 安装项目需要的依赖（由于本项目包含了HoshinoBot的所有依赖，所以只需要两条指令哦）
```sh
cd koinoribot
pip3.8 install -r requirements.txt
```
- HoshinoBot项目有一些默认配置需要导入哦(HoshinoBot/hoshino/)
```sh
cd ../../
mv ./config_example ./config
```
- 将本项目加载到HoshinoBot
```sh
cd config
```
- 在 `__bot__.py` 中的 `MODULES_ON` 里新增一行 `"koinoribot",`，但我不会用命令行填进去
- 所以……麻烦你使用vi手动填一下吧
```sh
vi __bot__.py
```
- 终于，到最后一步啦~
- 去Hoshinobot根目录启动一下吧~
```sh
cd ../../ 
python3.8 run.py
```

# 部署后的使用方法
- 进入机器人的根目录
```sh
cd HoshinoBot
```
- 启动虚拟环境
```sh
source venv/bin/activate
```
- 启动机器人
```sh
python3.8 run.py
```


<details>
 <summary> 注意事项 </summary> 

 - 如果在安装依赖的过程中出现错误，请务必及时解决，通常都可在百度上找到解决方案。
 
 
 - 关于部分插件需要用到的静态图片资源文件与字体文件，恕不在此公开。如有需要可以移步[![插件试用群](https://img.shields.io/badge/插件试用-冰祈杂谈分铺-brightgreen)](https://jq.qq.com/?_wv=1027&k=fdFbP60u)。
 
 
 - 部分功能需要申请api，请将相应的api填进 `koinoribot/config.py` 里以正常使用插件。
 
 
 - 部分功能如 `语音版网易云点歌` 需要用到`ffmpeg`，在[官网](https://ffmpeg.org/download.html)下载后解压至任意位置，并在环境变量`Path`中添加`ffmpeg.exe`所在路径。
 
 
 - 部分插件在下载图片时需要走代理，可以在 `koinoribot/config.py` 的 `proxies` 栏内进行配置。推荐使用 [clash](https://github.com/Fndroid/clash_for_windows_pkg)
</details>



<details>
 <summary> 关于Hoshinobot </summary> 

- 仓库传送门 [Hoshinobot](https://github.com/Ice9Coffee/HoshinoBot) (作者： [Ice9Coffee](https://github.com/Ice9Coffee))

</details>


## 个人部署环境参考
 - 操作系统：Debian 12.10
 - Python版本：3.8.0

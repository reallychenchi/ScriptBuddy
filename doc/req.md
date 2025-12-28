# ScriptBuddy 台词本项目

## 概述

这是一个用来帮助用户背台词的项目，用到语音识别转文字、文字转语音功能。
具备面向用户的前端和面向管理的后端。此次需求只讨论前端，前端需要具备转向客户端的能力。

## 需求

首先实现网页版本，目前只要求中文版本，但是要支持国际化能力，保留多语言支持。

一个网页上完成功能。流程如下

### 前端启动
申请和检查必要的权限，目前看有：
* 音量是否足够大
* 麦克风权限是否已经有
如果没有，需要在界面上提示用户，用较大字体提示

### 界面布局

手机端竖屏情况下，界面分成两部分，上半部分台词区域和下半部分语音区域。横屏情况下分成左右两部分，左半部分是台词区域，右半部分是语音区域。

平板端和手机端一样处理。

#### 台词区域
台词有三种：甲乙合，甲乙是两个主持人，合代表他们一起说的内容。
在台词区域除了展示台词，还要展示一些询问、交互内容。都是用文字方式。字号要大，让人看清楚。
询问内容用 红色
交互内容用 深绿色
台词区域背景色是白色
用户的台词用 黑色/灰色/白色 （不同状态，刚刚开始用黑色，背得比较熟了用灰色，最后默背用台词区域背景色）
和用户对台词（就是我们软件）的台词用 深蓝色/白色（不同状态，平时用蓝色，最后默背用台词区域背景色）

展示的时候，交互、询问内容一次全部展示上去，会控制长度确保能完全展示；
用户的台词按照不同的速率展示，一次展示一段台词，识别到用户说完了替换。
软件的台词一次展示一段，语音合成说完了以后替换

#### 语音区域
语音区域展示一个Lottie动画，在不同状态展示不同的动画：
询问、交互、念软件台词的时候展示正在说话的动画
等待用户的时候展示等待的动画


## 技术约束
使用PHP 5.2 作为后端
前端使用 SAP + React模式开发
语音识别和文字转换使用豆包方案

### 豆包流式语音识别模型2.0
语音转文字
https://console.volcengine.com/speech/service/10038?AppID=<YOUR_APP_ID>
appid V2L_APPID

AccessToken .env V2L_ACCESS_TOKEN

Secret key .env V2L_SECRET_KEY

接入文档： api方式 https://www.volcengine.com/docs/6561/1354869?lang=zh
sdk方式 https://www.volcengine.com/docs/6561/1354869?lang=zh

### 语音合成大模型

https://console.volcengine.com/speech/service/10007?AppID=<YOUR_APP_ID>

appid L2V_APPID

AccessToken .env L2V_ACCESS_TOKEN

Secret key .env L2V_SECRET_KEY

api接入： https://www.volcengine.com/docs/6561/1257584
sdk接入：https://www.volcengine.com/docs/6561/79827?lang=zh


# vsconvert

#### 介绍
版本转换工具

#### 软件架构
python


#### 安装教程

1.  pyinstaller genaric.spec 生成exe二进制文件
2.  配置配置文件
3.  xxxx

#### 使用说明

1. groups.yaml 中创建主机(文件夹)组群相关信息，可将部分主机设定为一个组，方便后面的action文件调用
2. 按需创建action文件，action.yaml是默认文件，文件名称可自定义 cmd>vsconvert.exe #运行的是action.yaml中的配置 cmd>vsconvert.exe test.yaml #运行的是config/test.yaml 中的配置
3. 建议创建指定bat文件，关联action文件，以方便执行相关任务

#### action文件配置说明
```yaml
PUBLIC:
  # 公共设置部分
  公共参数key: 公共参数value
  source: C:\Users\hp\Desktop\临时文件夹\vsconvert\dir1\tra # 版本转换源目录
  dest: C:\Users\hp\Desktop\临时文件夹\vsconvert\dir2\tra   # 版本转换目标目录
ACTION:
  - hosts: [Simutransaction1, Simutransaction2]  # source 下面的文件夹
    # hosts: ALL 表示对source目录下所有子文件夹进行操作
    # 
    tasks:
      - name: 任务说明
        vscs:  # 调用的模块，下面的设置都是模块相关的设置       
          模块参数1: 模块参数1value
          模块参数2: 模块参数2value
```

###### vsc，版本转换模块1
模块将循环读取source/hosts配置下面的的文件及目录，对文件拷贝到dest/hosts文件夹下（copy_exclude配置的除外），
并根据版本转换规则进行转换。

*模块参数*

```yaml
               'conf\*.cfg': # 指定需要修改的文件范围
                 # 下面是对指定文件的修改策略，可进行多个修改规则的制定，如IP修改，dev修改等等
                 # ip 转换
                 - regexp: '10\.(\d+)\.(\d+)\.(\d+)'
                   replace: '20.\1.\2.\3'
                 # DEV 转换 ,alert_exclude 中指定无需转换的文件
                 - regexp: '"dev"(.*)(\d)(\d)(\d)'
                   replace: '"dev"\g<1>\g<2>3\g<4>'
                   alert_exclude: []
               '*.sh':
                 - regexp: 'INIT_DEV_ID=(\d)(\d)(\d)'
                   replace: 'INIT_DEV_ID=\g<1>3\3'
                   alert_exclude: []
               # copy_exclude中指定无需进行复制的文件
               copy_exclude: ['.[clmsv]*', '*.result', 'info.*', '*.info','oradiag*','sunyardlog']
```


###### vscs，版本转换模块2
模块将循环读取source/hosts配置下面的的文件及目录，对文件拷贝到dest/hosts文件夹下（copy_ignores配置的除外），
并根据版本转换规则进行转换，dirs与rpls配置必须成对配置，vscs模块将所有dest/hosts目录下dirs配置的文件或目录进行rpls下面的转换

*模块参数*
```yaml
          - copy_ignores:
              ignores: ['*2020*','*cfg']
          - dirs:
              - 'conf\': +r
              - '*.sh':
          - rpls:
              # IP 转换
              - regexp: '12.1.x.x'
                replace: '22.1.x.x'
                alter_exclude: []
              # dev 转换
              - regexp: 'INIT_DEV_ID=(\d)(\d)(\d)'
                replace: 'INIT_DEV_ID=\g<1>3\3'
                alter_exclude: []
              
              - regexp: '"dev" : (\d)(\d)(\d)'
                replace: '"dev" : \g<1>3\3'
                alter_exclude: []
          - dirs:
              - 'conf_1\': +r
              - '*.sh.bak':
          - rpls:
              # IP 转换
              - regexp: '12.1.110.38'
                replace: '22.1.110.30'
                alter_exclude: [ ]
```
#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request




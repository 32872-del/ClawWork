

# tips
    - 优先get，尝试数据能不能直接get出来，不行修改header ，不行使用curl_cffi模式
    - get请求到的可能和页面不一样
    - 用get可以多加线程数
## CrawlerObject类说明
    driver1 playwright 的配置项
    driver2 botasaurus 的配置项
    is_recollect 是否新建数据库 0否 选择最新的数据库追加写入
    collect_thread_number 线程数 get_content  + get_more_content  = 2*collect_thread_number
    **name** 数据库名称以及目录名称
## 新增
    采集去重
    进度保持
    代理设置
    采集情况查看
    支持get_more_content导出列表数据 []


    *** 根据导出的url来去重，如果get_more_content中导出多条数据，每条数据的url要手动不同






## 请求参数及方法说明

### 全局参数
    d1 driver1 启动配置
    d2 driver2 启动配置
    new - is_recollect：是否重新采集默认1 为0则在上一个采集的基础上重新采集，读取上一次的记录
    new - is_proxy：是否使用代理，目前只支持get和post 默认0 为1全部请求都使用代理 如果单独使用代理在请求的时候自己配置


### get请求，可用参数：request_type, cache, save
    request_type：默认requests，可选curl_cffi 使用curl进行请求，加参数impersonate="chrome"过简单反爬

### post请求，可用参数：request_type
    request_type：默认requests，可选curl_cffi 使用curl进行请求，加参数impersonate="chrome"过简单反爬

### render_page请求，可用参数：return_driver，sleep_time，save，cache，**driver_type**
    return_driver：必要时可导出driver进行页面操作 默认为False 如果是driver_type1，完成操作进行driver.close()关闭
    sleep_time：强制渲染时间
    driver_type：默认为1 
       1使用 playwright 进行自动化 **速度快，防爬程度低**
       2使用 botasaurus 进行自动化 **速度慢，防爬程度高**




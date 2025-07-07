import requests
import os
from bs4 import BeautifulSoup
import json
import base64

def to_base64(data):
    return base64.b64encode(data.encode('utf-8')).hex()

def mock_headers():
    return {
        "user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "max-age=0",
        "if-modified-since": "Mon, 25 Jan 2021 22:04:08 GMT",
        "if-none-match": "\"a15c2ac3234aa8f6064ef9c1f7383c37\"",
        "priority": "u=0, i",
        "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1"
    } 

def get_http_resource(url):
    if url.find("msgType_") >= 0:
        print("hello")
    print("fetching url: " + url)
    resp = requests.get(url, headers=mock_headers())
    if resp.status_code == 200:
        print("fetch url OK: " + url)
        return resp.text
    else:
        print("fetch url failed: " + url)
        return ""
        
def parse_html(text):
    soup = BeautifulSoup(text, 'html.parser')
    return soup

def exist_local_file(filepath):
    return os.path.exists(filepath)

def save_file(filepath, text, override=False):
    dir = os.path.dirname(filepath)
    if not os.path.exists(dir):
        os.makedirs(dir)
    if not os.path.exists(filepath) or override is True:
        f = open(filepath, "w", encoding="utf-8")
        f.write(text)
        f.close()
    
def fetch_or_read_local(filepath, url):
    if os.path.exists(filepath):
        print("read file from local: ", filepath)
        f = open(filepath, "r", encoding="utf-8")
        cont = f.read()
        return cont
    else:
        cont = get_http_resource(url)
        return cont

def fetch_and_save_html_file(filename, url):
    # raw filename
    filename = get_local_filename(RAW_DIR, filename)
    if os.path.exists(filename):
        print("read html from local: " + filename)
        f = open(filename, "r", encoding="utf-8")
        text = f.read()
        return text
    else:
        html = get_http_resource(url)
        save_file(filename, html)
        return html

def get_local_filename(base_dir, filename):
    return os.path.join(base_dir, filename)        
     
    
def get_full_url(url):
    if url.find("http") < 0:
        if url.find("/") == 0:
            url = url[1:]
        return os.path.join(BASE_URL, url)
    return url

def split_url_for_filename(url):
    index = url.rfind("/")
    if index >= 0:
        return url[index+1:]
    return url

def parse_for_sub_page_urls(soup):
    a_list = soup.find_all('a')
    filter_a_list = []
    for item in a_list:
        if 'href' in item.attrs:
            url = item.attrs['href']
            if filter_url(url):
                filter_a_list.append(url)
                # print(url)
    return filter_a_list

def filter_url(url):
    if url is None:
        return False
    if url.find(".html") < 0:
        return False
    if url.find("msgs_") < 0 and url.find("fields_") < 0 and url.find("tagNum_") < 0 and url.find("msgType_") < 0:
        return False
    return True

def handle_html(filename, soup, override=False):
    print("======= handle html =========")
    # parse for sub pages
    sub_node_list = []
    urls = parse_for_sub_page_urls(soup)
    # print("sub urls: ")
    for url in urls:
        newNode = NodeInfo(split_url_for_filename(url), get_full_url(url))
        sub_node_list.append(newNode)
        # print(newNode.to_json())
    
    # check target html file
    target_filename = get_local_filename(TARGET_DIR, filename)
    if exist_local_file(target_filename) and not override:
        print("target filename already exists, ignore: ", target_filename)
        return sub_node_list
    # replace urls
    html = soup.prettify()
    for node in sub_node_list:
        sub_url = os.path.join("./", node.filename)
        if html.find(node.url) >= 0:
            html = html.replace(node.url, sub_url)
        else:
            html = html.replace(node.filename, sub_url)
    save_file(target_filename, html, override)
    return sub_node_list
    
def handle_css(soup):
    print("======= handle css =========")
    links = soup.find_all('link', rel="stylesheet")
    css_list = []
    for link in links:
        url = link.attrs["href"]
        filename = split_url_for_filename(url)
        print(filename, url)
        css_list.append(NodeInfo(filename, url))
        
        # fetch and save files
        raw_filepath = os.path.join(RAW_DIR, STATIC_DIR, filename)
        target_filepath = os.path.join(TARGET_DIR, STATIC_DIR, filename)
        if not exist_local_file(raw_filepath):
            content = get_http_resource(url)
            save_file(raw_filepath, content)
            save_file(target_filepath, content)   
        # replace
        new_href = os.path.join("./", STATIC_DIR, filename)
        # new_href = os.path.join(STATIC_DIR, filename)
        link.attrs["href"] = new_href
    return soup

def handle_js(soup):
    print("======= handle js =========")
    links = soup.find_all('script')
    for link in links:
        if not link.has_attr("src"):
            continue
        url = link.attrs["src"]
        url = get_full_url(url)
        filename = "{}.js".format(to_base64(url))
        if len(filename) > 100:
            filename = filename[-100:]
        # print(filename, url)
        
        # fetch and save files
        raw_filepath = os.path.join(RAW_DIR, STATIC_DIR, filename)
        target_filepath = os.path.join(TARGET_DIR, STATIC_DIR, filename)
        if not exist_local_file(raw_filepath):
            content = get_http_resource(url)
            save_file(raw_filepath, content)
            save_file(target_filepath, content)   
        # replace
        new_src = os.path.join(STATIC_DIR, filename)
        link.attrs["src"] = new_src
    return soup
        

class NodeInfo:
    def __init__(self, filename, url):
        self.filename = filename
        self.url = url
    def to_json(self):
        return json.dumps(self.__dict__)

def traversal_fetch_html(node: NodeInfo, depth=1):
    cur_depth = 1
    node_list = []
    sub_node_list = []
    sub_node_list.append(node)
    
    while cur_depth <= depth:
        node_list = sub_node_list
        sub_node_list = []
        print("===> process html at depth: ", cur_depth)
        while(len(node_list) > 0):
            item = node_list.pop()   
            print("============handle page ===========")         
            print("page url=", item.url)
            html = fetch_and_save_html_file(item.filename, item.url)
            soup = parse_html(html)
            # soup = handle_css(soup)
            soup = handle_js(soup)
            
            # handle current html page
            sub_nodes = handle_html(item.filename, soup, override=False)
            sub_node_list.extend(sub_nodes)
        
        # move to next level
        cur_depth = cur_depth + 1
    


RAW_DIR = "./raw"   # 存放原始文件
TARGET_DIR = "./target" # 存放修改后的html
STATIC_DIR = "static" # css, js等文件的目录
BASE_URL = "https://www.onixs.biz/fix-dictionary/4.2"

def main():
    index_url = get_full_url("index.html")
    index_filename = "index.html"
    node = NodeInfo(index_filename, index_url)
    
    traversal_fetch_html(node, depth=3)  

def test():
    test = True

if __name__ == "__main__":
    test()
    main()
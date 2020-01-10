# trojan-caddy-docker-compose

Trojan server and Caddy integration with Docker compose。

Trojan server listens port 443. For https requests from normal sources, Trojan server will forward them to Caddy server for processing and return to the Web page while requests from Trojan client will be proxied by Trojan server which like V2ray+Websocket+TLS avoid GFW detection by disguising requests.

使用 docker-compose 构建的 Trojan Server + Caddy Web Server。

Trojan 服务端监听 443 端口，对正常来路的 https 请求，Trojan 服务端会转发给 Caddy 服务器处理，返回 Web 页面；而通过 Trojan 客户端来的请求，则由 Trojan 服务端进行代理，与 V2ray + Websocket + TLS 的原理一样，通过伪装流量，避免被 GFW 提取特征与检测。

部署教程：https://muguang.me/it/2757.html

## Usage

Git clone this repo then change directory to this project.

1. Modify `./caddy/Caddyfile`:
    ```
    www.yourdomain.com:80 {
        root /usr/src/trojan
        log /usr/src/caddy.log
        index index.html
    }

    www.yourdomain.com:443 {
        root /usr/src/trojan
        log /usr/src/caddy.log
        index index.html
    }
    ```
    Replace `www.yourdomain.com` with your own domain name.

2. Modify `./trojan/config/config.json`:

    Change `your_password` to your own password on `config:json:8` , this is your trojan password just safekeeping.
    
    Change `your_domain_name` to your own domain name on `config:json:12-13`, this is your domain ssl certification path, Caddy server generate certs automatically on the path `/ssl/your_domain_name/your_domain_name.crt`
 
3. Run `docker-compose up` or `docker-compose up -d`  with Daemon mode
4. When each container is successfully built, it means that your Trojan and Caddy servers are working well.


## Tips

考虑到各种未知状况，如果构建过程中遇到任何问题可以在`issue`中提出。

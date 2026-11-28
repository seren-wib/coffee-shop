# gunicorn settings (SDD 11.2, 12.1): 3 sync workers, 30 s request limit.
bind = "unix:/run/coffee-shop/gunicorn.sock"
workers = 3
worker_class = "sync"
timeout = 30
umask = 0o007  # the socket is reachable by the coffee-shop group (nginx's www-data is in it)
accesslog = None  # nginx keeps the access log (SDD 9.5)
errorlog = "-"  # journald
control_socket_disable = True  # gunicorn 27 control socket lives in $HOME; the app account has none

from werkzeug.middleware.proxy_fix import ProxyFix
from application import create_app

app = create_app()
# Trust Render's reverse proxy (X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == "__main__":
    app.run()

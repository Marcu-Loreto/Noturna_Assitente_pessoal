"""
Google OAuth Setup — Run once to authorize Gmail + Calendar access.
Keeps the MCP server running while you authorize in the browser.

Usage:
    uv run python setup_google_auth.py
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time

from dotenv import load_dotenv

load_dotenv()


def main():
    env = {**os.environ, "OAUTHLIB_INSECURE_TRANSPORT": "1"}
    email = os.environ.get("USER_GOOGLE_EMAIL", "")

    if not email:
        print("❌ USER_GOOGLE_EMAIL não encontrado no .env")
        sys.exit(1)

    print(f"\n🔐 Iniciando Google Workspace MCP para autorização...")
    print(f"   Conta: {email}")
    print(f"   OAuth callback: http://localhost:8000/oauth2callback\n")

    proc = subprocess.Popen(
        ["workspace-mcp", "--tools", "gmail", "calendar", "--single-user", "--tool-tier", "core"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Stream stderr so user sees the auth URL
    def stream_stderr():
        for line in proc.stderr:
            text = line.decode().strip()
            if text:
                # Highlight the auth URL
                if "accounts.google.com" in text and "Authorization URL:" in text:
                    url = text.split("Authorization URL: ")[-1].strip()
                    print(f"\n{'='*60}")
                    print(f"🔗 ABRA ESTA URL NO BROWSER:")
                    print(f"\n{url}\n")
                    print(f"{'='*60}\n")
                elif "accounts.google.com" not in text:
                    print(f"  [MCP] {text}")

    t = threading.Thread(target=stream_stderr, daemon=True)
    t.start()

    time.sleep(3)

    def send(data):
        proc.stdin.write((json.dumps(data) + "\n").encode())
        proc.stdin.flush()

    def recv():
        line = proc.stdout.readline()
        return json.loads(line.decode().strip()) if line else None

    # Initialize MCP
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "setup", "version": "1.0.0"},
    }})
    resp = recv()
    if not resp:
        print("❌ Falha ao inicializar")
        proc.terminate()
        return

    print("✅ MCP server inicializado")

    # Send initialized notification
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    time.sleep(1)

    # Trigger auth by calling list_calendars
    print(f"\n📅 Solicitando acesso ao Calendar + Gmail...")
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "list_calendars",
        "arguments": {"user_google_email": email},
    }})

    # Read the response (will contain auth URL)
    time.sleep(3)
    resp = recv()

    if resp and "result" in resp:
        content = resp["result"].get("content", [])
        needs_auth = any("ACTION REQUIRED" in item.get("text", "") for item in content)

        if needs_auth:
            print("⏳ Aguardando autorização no browser...")
            print("   Depois de autorizar, aguarde alguns segundos.\n")
            print("   Pressione Enter DEPOIS de autorizar no browser.")
            input("\n   [Enter para continuar] ")

            # Retry
            time.sleep(2)
            send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "list_calendars",
                "arguments": {"user_google_email": email},
            }})
            time.sleep(5)
            resp = recv()

    # Check result
    success = False
    if resp and "result" in resp:
        content = resp["result"].get("content", [])
        for item in content:
            text = item.get("text", "")
            if "ACTION REQUIRED" not in text and len(text) > 10:
                print(f"\n✅ Calendar OK!")
                print(text[:300])
                success = True
                break

    if not success:
        print("\n⚠️  Calendar ainda não autorizado.")
        print("   Verifique se autorizou no browser corretamente.")

    # Test Gmail
    print(f"\n📧 Testando Gmail...")
    send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "search_gmail_messages",
        "arguments": {"user_google_email": email, "query": "is:inbox", "max_results": 2},
    }})
    time.sleep(5)
    resp = recv()

    if resp and "result" in resp:
        content = resp["result"].get("content", [])
        for item in content:
            text = item.get("text", "")
            if "ACTION REQUIRED" not in text and len(text) > 10:
                print(f"✅ Gmail OK!")
                print(text[:300])
                break
            elif "ACTION REQUIRED" in text:
                print("⚠️  Gmail precisa de autorização.")
                print("   Abra a URL que apareceu acima e autorize.")
                input("\n   [Enter depois de autorizar] ")
                # Retry
                send({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
                    "name": "search_gmail_messages",
                    "arguments": {"user_google_email": email, "query": "is:inbox", "max_results": 2},
                }})
                time.sleep(5)
                resp2 = recv()
                if resp2 and "result" in resp2:
                    for item2 in resp2["result"].get("content", []):
                        text2 = item2.get("text", "")
                        if "ACTION REQUIRED" not in text2:
                            print(f"✅ Gmail OK!")
                            print(text2[:300])

    print("\n🎉 Setup concluído! Tokens salvos em ~/.google_workspace_mcp/credentials/")
    print("   Agora rode: uv run python noturna_client.py\n")

    proc.terminate()
    proc.wait(timeout=5)


if __name__ == "__main__":
    if not os.environ.get("GOOGLE_OAUTH_CLIENT_ID"):
        print("❌ GOOGLE_OAUTH_CLIENT_ID não encontrado no .env")
        sys.exit(1)
    main()

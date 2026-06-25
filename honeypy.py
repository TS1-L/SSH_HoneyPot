import argparse
from ssh_honeypot import *
from web_honeypot import *

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSH_HoneyPot - A modular honeypot for capturing attack data.")
    parser.add_argument('-a', '--address', type=str, required=True, help='Bind address (use 0.0.0.0 for all interfaces)')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('-u', '--username', type=str, help='Username to authenticate with (default: accept all)')
    parser.add_argument('-w', '--password', type=str, help='Password to authenticate with (default: accept all)')
    parser.add_argument('-s', '--ssh', action="store_true", help='Run SSH honeypot')
    parser.add_argument('-t', '--tarpit', action="store_true", help='Enable SSH tarpit (endless banner)')
    parser.add_argument('-wh', '--http', action="store_true", help='Run HTTP WordPress honeypot')

    args = parser.parse_args()

    try:
        if args.ssh:
            print("[-] Running SSH Honeypot...")
            honeypot(args.address, args.port, args.username, args.password, args.tarpit)

        elif args.http:
            print('[-] Running HTTP Wordpress Honeypot...')
            if not args.username:
                args.username = "admin"
                print("[-] Running with default username of admin...")
            if not args.password:
                args.password = "deeboodah"
                print("[-] Running with default password of deeboodah...")
            print(f"Port: {args.port} Username: {args.username} Password: {args.password}")
            run_app(args.port, args.username, args.password)
        else:
            print("[!] You can only choose SSH (-s) (-ssh) or HTTP (-h) (-http) when running script.")
    except KeyboardInterrupt:
        print("\nProgram exited.")

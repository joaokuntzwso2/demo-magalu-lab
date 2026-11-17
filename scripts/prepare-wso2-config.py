"""Render LOCAL-only WSO2 config. Passwords never printed/logged."""
import os
from pathlib import Path

def valid_public_host(hostname):
    import ipaddress
    import re

    if not hostname:
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return re.fullmatch(
            r'[a-z0-9-]+(?:[.][a-z0-9-]+)+',
            hostname
        ) is not None

    return isinstance(address, ipaddress.IPv4Address) and address.is_global


def main():
    mode=os.getenv('MAGALU_ENV_MODE','legacy')
    template=Path('docker/wso2/deployment.isolated.template.toml' if mode=='isolated' else 'docker/wso2/deployment.template.toml')
    result=template.read_text()

    public_url=os.environ.get(
        'IS_PUBLIC_URL','https://localhost:9543'
    ).rstrip('/')

    if public_url != 'https://localhost:9543':
        import json
        import re
        from urllib.parse import urlsplit

        parsed=urlsplit(public_url)
        hostname=parsed.hostname

        valid=(
            parsed.scheme == 'https'
            and hostname is not None
            and parsed.netloc == hostname
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and valid_public_host(hostname)
        )

        if not valid:
            raise SystemExit(
                'IS_PUBLIC_URL must be an HTTPS public DNS or IPv4 origin '
                'without a port, path or credentials'
            )

        replacements={
            'hostname = "localhost"':
                'hostname = '+json.dumps(hostname),
            'base_path = "https://$ref{server.hostname}:${carbon.management.port}"':
                'base_path = '+json.dumps(public_url),
        }

        for old,new in replacements.items():
            if result.count(old)!=1:
                raise SystemExit(
                    'Unexpected WSO2 template structure: '+old
                )
            result=result.replace(old,new,1)

        sections=(
            '[transport.https.properties]',
            '[console]',
            '[myaccount]',
        )

        if any(section in result for section in sections):
            raise SystemExit(
                'WSO2 template already defines a public section; '
                'review before changing it'
            )

        # Declare [console] before its existing child table.
        console_marker = '[console.flows.scopes]'
        console_block = (
            '[console]\n'
            'callback_url = '
            + json.dumps(public_url + '/console') + '\n\n'
        )

        if mode == 'isolated':
            if result.count(console_marker) != 1:
                raise SystemExit(
                    'Unexpected isolated template: console scopes missing'
                )
            result = result.replace(
                console_marker, console_block + console_marker, 1
            )
        else:
            result += '\n' + console_block

        result += (
            '\n[transport.https.properties]\n'
            'proxyPort = 443\n'
            '\n[myaccount]\n'
            'callback_url = '
            + json.dumps(public_url + '/myaccount') + '\n'
        )
    for key in ('IS_ADMIN_PASSWORD','IS_DB_USER','IS_DB_PASSWORD'):
        if '${'+key+'}' not in result:
            continue
        value=os.environ.get(key,'')
        if not value or any(c in value for c in ('\\','"','\r','\n')):
            raise SystemExit(f'{key} is missing or contains unsupported TOML characters')
        result=result.replace('${'+key+'}',value)
    target=Path('generated/wso2/deployment.toml')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(result)
    target.chmod(0o600)
    print('Rendered',target,'mode:',mode,'(secrets hidden)')

if __name__=='__main__':
    main()

"""Section 7 guided test catalog for the existing Magalu Architecture Lab.

Read-only navigation: never runs an operator action, leaks a manifest, or
manufactures a PASS. Tests execute through their pre-existing workbenches.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRoute
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))

# All route references are static local paths, or explicitly known localhost ports.
# Never use a browser-supplied destination for test navigation.
TESTS = [
    dict(id='architecture', phase='01', code='7.1', title='Arquitetura e root tenants',
         summary='Apresente as duas fronteiras de identidade e o mapa de aplicações.',
         path='/', kind='page', requirement='Dois root tenants independentes, três marcas.',
         steps='Verifique magalu.demo e magalupay.demo; confira o inventário de apps no bootstrap.',
         evidence='Inventário de tenants, clientes e configuração de issuer.'),
    dict(id='readiness', phase='01', code='7.1', title='Cockpit de aceitação da Seção 7',
         summary='Execute os testes consolidados já disponíveis no servidor.',
         path='/s7/acceptance', kind='page', requirement='Inventário de critérios, resultados e bloqueios.',
         steps='Abra o cockpit e siga os cenários habilitados sem tratar bloqueios como aprovação.',
         evidence='Resultados efetivos da API e evidências exportáveis.'),
    dict(id='magalu_web', phase='02', code='7.2 #1 · PF', title='Magalu Retail · Web',
         summary='Login OIDC do canal web com cliente e sessão próprios.', path='http://localhost:8181',kind='external',
         requirement='Autenticação PF real em cliente web independente.',
         steps='Abrir em nova aba privada; autenticar ana.magalu; verificar sessão e logout.',
         evidence='Login real, issuer, sub, audience e logout.'),
    dict(id='magalu_mobile', phase='02', code='7.2 #1 · PF', title='Magalu Retail · Mobile',
         summary='Canal mobile simulado com OIDC próprio.', path='http://localhost:8182', kind='external',
         requirement='Continuidade de identidade dentro da marca.',
         steps='Entrar com a mesma identidade de Magalu Web; comparar os subjects observados.',
         evidence='Sub assinado do segundo cliente e sessão isolada.'),
    dict(id='netshoes_web', phase='02', code='7.2 #1', title='Netshoes · Web',
         summary='Outra marca do tenant Commerce, sem reutilizar a sessão do Magalu.',
         path='http://localhost:8183', kind='external',
         requirement='Segregação de sujeito pairwise entre marcas.',
         steps='Entrar com a identidade de teste correlacionada; observar sub e claims.',
         evidence='Sub assinado e sessão independente.'),
    dict(id='netshoes_mobile', phase='02', code='7.2 #1', title='Netshoes · Mobile',
         summary='Continuidade por marca, separação em relação a Magalu.',
         path='http://localhost:8184', kind='external',
         requirement='Mesmo setor Netshoes, novo cliente OIDC.',
         steps='Autenticar e comparar pairwise com Netshoes Web.',
         evidence='Sub e audience de Netshoes Mobile.'),
    dict(id='pay_web', phase='02', code='7.2 #1', title='MagaluPay · Web',
         summary='Login sob o root tenant independente magalupay.demo.',
         path='http://localhost:8185', kind='external',
         requirement='Tenant distinto, isolamento de sessão e de sujeito.',
         steps='Entrar com o usuário local do tenant Pay; não presumir SSO entre raízes.',
         evidence='Issuer Pay e sub assinado.'),
    dict(id='pay_mobile', phase='02', code='7.2 #1', title='MagaluPay · Mobile',
         summary='Segundo cliente da raiz Pay.', path='http://localhost:8186', kind='external',
         requirement='Continuidade interna do setor Pay.',
         steps='Entrar e comparar sub com MagaluPay Web.',
         evidence='Sub assinado de Pay Mobile.'),
    dict(id='pairwise', phase='03', code='7.2 #1', title='Matriz pairwise de seis canais',
         summary='Compare sub real observado nas seis sessões BFF.', path='/pairwise', kind='page',
         requirement='Sub igual dentro de uma marca e diferente entre marcas, para a mesma pessoa.',
         steps='Autentique os seis canais no mesmo navegador; abra a matriz e avalie as comparações.',
         evidence='Matriz de sujeitos reais; não equivale automaticamente a prova de configuração OIDC.'),
    dict(id='pairwise_api', phase='03', code='7.2 #1', title='Evidência pairwise · JSON',
         summary='Resultado de leitura somente derivado de sessões observadas.',
         path='/api/pairwise-evidence',kind='evidence',
         requirement='Guardar estado e divergências sem publicar bearer tokens.',
         steps='Abrir depois dos logins; salvar o JSON para evidência.',evidence='JSON com checks observados.'),
    dict(id='claims', phase='03', code='7.2 #2', title='Claims por canal e finalidade',
         summary='Compare scopes, audience e atributos liberados por aplicação.', path='/m3/completion',kind='page',
         requirement='Claims mínimos e diferenciação entre aplicativos.',
         steps='Use as abas de PF; inspecione as evidências dos clientes reais.',
         evidence='ID token, UserInfo e acesso autorizado, com valores sensíveis omitidos.'),
    dict(id='consent', phase='04', code='7.2 #4', title='Consentimento direcional · Ledger',
         summary='Criar, conceder, negar e revogar consentimento entre marcas.',
         path='/m3/consent',kind='page',
         requirement='Histórico independente e decisão de acesso no recurso protegido.',
         steps='Autentique origem e destino; crie vínculo; tente leitura sem grant; conceda e revogue.',
         evidence='Estados GRANTED/REVOKED e resposta 403 após revogação.'),
    dict(id='native_consent', phase='04', code='7.2 #4', title='Consentimento nativo WSO2 v2',
         summary='Valide o registro nativo e a regra de dupla autorização.',
         path='/m3/native-consent',kind='page',
         requirement='Acesso exige concessão nativa e do ledger de negócio.',
         steps='Execute preflight, concessão explícita, leitura, revogação e nova leitura.',
         evidence='Readback nativo e razão da decisão; pode exigir chave de operador.'),
    dict(id='isolation', phase='04', code='7.1 · 7.2 #4', title='Isolamento entre root tenants',
         summary='Comprove as fronteiras Commerce / Pay e controles de consentimento.',
         path='/m3/isolation',kind='page',
         requirement='Não reutilizar identidade, token ou consentimento entre raízes.',
         steps='Autentique as aplicações relevantes; execute os controles e casos negativos.',
         evidence='Evidência real de fronteira; não implica federação pronta.'),
    dict(id='exchange', phase='05', code='7.2 #5', title='Token Exchange · RFC 8693',
         summary='Compare sujeito, ator, escopo, audience e recusa de escalada.',
         path='/m3/exchange',kind='page',
         requirement='Delegação auditável, emissão verificável e redução de privilégios.',
         steps='Execute subject-only, delegated read e tentativa de scope escalation.',
         evidence='HTTP, sub, act.sub, escopos e verificação criptográfica.'),
    dict(id='m2m', phase='05', code='7.3 · M2M', title='Client Credentials · emissão básica',
         summary='Gere evidência de um token de serviço, sem exibir segredos.',
         path='/m2m',kind='page',
         requirement='Grant client_credentials funcional e sem exposição de token bruto.',
         steps='Solicite um token e confira status, issuer e escopo disponível.',
         evidence='Resultado HTTP seguro; não equivale a ensaio de carga.'),
    dict(id='seller', phase='06', code='7.2 #6 · PJ', title='Login B2B / Seller · LDAP',
         summary='Autentique SELLERLDAP/ldap.seller e valide permissões por aplicação.',
         path='/m3/completion',kind='page',
         requirement='Dois user stores e autenticação externa via OpenLDAP.',
         steps='Use a aba B2B; login com SELLERLDAP/ldap.seller, password definido no LDAP; teste papel autorizado e negado.',
         evidence='SCIM user, autenticação real, roles e decisão de autorização.'),
    dict(id='seller_business', phase='06', code='7.3 · PJ', title='Painel Seller · autorização de negócio',
         summary='Acesso protegido após sessão do vendedor.',path='/seller',kind='page',
         requirement='Controle de mudança de conta / política de seller (fixture).',
         steps='Entrar no fluxo de seller antes de abrir a rota; executar teste autorizado e bloqueado.',
         evidence='Decisão de negócio, com limitação de step-up identificada.'),
    dict(id='tenant_growth', phase='06', code='7.2 #7', title='Onboarding de terceiro root tenant',
         summary='Fluxo de bootstrap e validação antes/depois.',path='/s7/acceptance',kind='page',
         requirement='Adicionar uma raiz sem transformar tenants existentes em organizações filhas.',
         steps='Execute scripts.onboard_brand pelo bootstrap, compare inventários e autentique no novo tenant.',
         evidence='Inventário antes/depois; login novo; raízes existentes inalteradas.'),
    dict(id='sessions_json', phase='07', code='7.1 · diagnóstico', title='Sessões observadas · JSON',
         summary='Matriz de estado de seis aplicações, somente leitura.',path='/api/evidence',kind='evidence',
         requirement='Evidência do estado sem compartilhar bearer tokens.',
         steps='Consulte antes e depois de login/logout e arquive resposta.',
         evidence='Status de sessão; não atribuir PASS pairwise apenas por sessão.'),
    dict(id='sessions_api', phase='07', code='7.1 · diagnóstico', title='Disponibilidade dos storefronts',
         summary='Status dos seis serviços a partir do navegador atual.',path='/api/storefront-status',kind='evidence',
         requirement='Diagnóstico de disponibilidade e autenticação por canal.',
         steps='Confirme disponível/autenticado após cada login.',evidence='JSON de availability/authenticated por canal.'),
]

PHASES = [
  ('01','Fundação','Arquitetura, readiness e inventário'),
  ('02','Jornada de autenticação','Seis experiências independentes'),
  ('03','Identidade e claims','Pairwise, minimização e validação'),
  ('04','Consentimento e isolamento','Conceder, revogar e impedir vazamentos'),
  ('05','Tokens e delegação','M2M básico e RFC 8693'),
  ('06','Seller e expansão','User stores, PJ e novo tenant'),
  ('07','Evidência operacional','Exportação e observação'),
]

DEFERRED = [
    {'name':'N2 / N3 e MFA step-up real','reason':'Não implantado nesta etapa. A fixture de política não prova ACR/AMR no WSO2.'},
    {'name':'M2M 1.000 tokens / carga','reason':'Fora do escopo atual. A emissão básica não certifica vazão, p95, p99 ou SLA.'},
    {'name':'Alta disponibilidade / produção','reason':'Laboratório localhost, single-node, TLS de desenvolvimento e segredos de PoC.'},
]

# Safe, non-API pages with static route paths only. Do not turn arbitrary API
# endpoints into a browser console; mutation APIs are deliberately excluded.
PREFIX_EXCLUDES = ('/api/', '/static/', '/sectors/', '/auth/', '/oauth2/', '/oidc/',
                   '/.well-known', '/healthz', '/docs', '/redoc', '/openapi')


def catalog_for(app):
    routes = {r.path for r in app.routes if isinstance(r, APIRoute) and 'GET' in r.methods}
    curated_paths = {t['path'] for t in TESTS if t['path'].startswith('/')}
    items=[]
    for test in TESTS:
        entry=test.copy()
        entry['available']=test['kind']=='external' or test['path'] in routes
        entry['link']=test['path'] if entry['available'] else None
        items.append(entry)
    # Future pages appear without hand-editing the catalog. Only known-safe,
    # concrete GET routes are eligible; no unknown dynamic path placeholders.
    additional=[]
    for path in sorted(routes - curated_paths):
        if path=='/lab' or path.startswith(PREFIX_EXCLUDES):
            continue
        if not path.startswith('/') or path == '/':
            continue
        if '{' in path or '}' in path:
            # Permit only a single, explicitly understood brand placeholder.
            if path.count('{brand}') != 1 or '{' in path.replace('{brand}','') or '}' in path.replace('{brand}',''):
                continue
            for brand in ('magalu','netshoes','magalupay'):
                concrete=path.replace('{brand}',brand)
                additional.append({'path':concrete,'title':concrete.strip('/').replace('/',' · ').replace('-',' ').title(), 'protected':True})
            continue
        additional.append({'path':path,'title':path.strip('/').replace('/',' · ').replace('-',' ').title(), 'protected':False})
    return items,additional


@router.get('/lab',response_class=HTMLResponse,include_in_schema=False)
def lab(request:Request):
    tests,additional=catalog_for(request.app)
    response=templates.TemplateResponse('lab_hub.html', {
        'request':request, 'brand':None, 'manifest':None, 'session':{},
        'tests':tests,'phases':PHASES,'additional':additional,'deferred':DEFERRED,
    })
    response.headers['Cache-Control']='private, no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response


@router.get('/api/lab/catalog',include_in_schema=False)
def lab_catalog(request:Request):
    tests,additional=catalog_for(request.app)
    r=JSONResponse({'kind':'section-7-lab-navigation','tests':tests,'discovered_pages':additional,
                    'deferred':DEFERRED,'note':'Availability is route discovery, NOT test PASS.'})
    r.headers['Cache-Control']='private, no-store'
    return r

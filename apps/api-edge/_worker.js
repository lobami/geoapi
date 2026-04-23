const UPSTREAM_BASE = 'http://toroto-origin.lobami.lat'
const ALLOWED_ORIGINS = new Set([
  'https://test-toroto.lobami.lat',
  'http://localhost:5173',
])

function corsHeaders(origin) {
  const allowedOrigin = ALLOWED_ORIGINS.has(origin) ? origin : 'https://test-toroto.lobami.lat'

  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Max-Age': '86400',
  }
}

export default {
  async fetch(request) {
    const origin = request.headers.get('Origin') || ''
    const headers = corsHeaders(origin)

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers,
      })
    }

    const url = new URL(request.url)
    const upstream = new URL(`${url.pathname}${url.search}`, UPSTREAM_BASE)
    const proxyHeaders = new Headers(request.headers)

    proxyHeaders.set('x-forwarded-host', url.host)
    proxyHeaders.set('x-forwarded-proto', 'https')
    proxyHeaders.delete('host')

    const response = await fetch(upstream, {
      method: request.method,
      headers: proxyHeaders,
      body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer(),
      redirect: 'manual',
    })

    const responseHeaders = new Headers(response.headers)
    Object.entries(headers).forEach(([key, value]) => responseHeaders.set(key, value))
    responseHeaders.set('x-edge-proxy', 'cloudflare-pages')

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    })
  },
}

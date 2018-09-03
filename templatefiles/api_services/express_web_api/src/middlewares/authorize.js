
const jwt = require('express-jwt');
const jwksRsa = require('jwks-rsa');


let issuer =  '{{issuer_host_dev}}';
if(process.env.ENVIRONMENT != 'Development'){
    issuer = '{{issuer_host}}';
}

const auhtorize = jwt({
    // secret: jwksRsa.expressJwtSecret({
    //     cache: true,        // see https://github.com/auth0/node-jwks-rsa#caching,        
    //     rateLimit: true,    // see https://github.com/auth0/node-jwks-rsa#rate-limiting
    //     jwksRequestsPerMinute: 5,
    //     jwksUri: `${issuer}/.well-known/jwks`
    // }),
    // validate the audience & issuer from received token vs JWKS endpoint
    audience: `${issuer}/resources`,
    issuer: issuer,
    secret: '{{api_secret}}',
    algorithms: ["RS256"]
});
module.exports = auhtorize;
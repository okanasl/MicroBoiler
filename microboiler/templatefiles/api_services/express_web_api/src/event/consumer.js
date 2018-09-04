var jackrabbit = require("jackrabbit");
var environment = process.env.ENVIRONMENT;
var rabbitUrl = 'ampq://'+process.env.EVENTBUS_USERNAME+':'+process.env.EVENTBUS_PASSWORD+'@'
if (environment == 'development')
{
    rabbitUrl+=EVENTBUS_HOST_DEV || "localhost:5672"
}else
{
    rabbitUrl+=process.env.EVENTBUS_HOST
}

var rabbit = jackrabbit(rabbitUrl);
var exchange = rabbit.fanout();
var logs = exchange.queue({ exclusive: true });

logs.consume(onLog, { noAck: true });
// logs.consume(false); // stops consuming

function onLog(data) {
  console.log("Received log:", data);
}
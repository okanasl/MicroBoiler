var jackrabbit = require("jackrabbit");
if (environment == 'development')
{
    rabbitUrl+=EVENTBUS_HOST_DEV || "localhost:5672"
}else
{
    rabbitUrl+=process.env.EVENTBUS_HOST
}
var rabbit = jackrabbit(rabbitUrl);
var exchange = rabbit.fanout();

exchange.publish("this is a log");
exchange.on("drain", process.exit);
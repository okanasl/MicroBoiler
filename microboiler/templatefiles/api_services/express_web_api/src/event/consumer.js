var jackrabbit = require("jackrabbit");
var environment = process.env.ENVIRONMENT;
var rabbitUrl = 'amqp://'+/*process.env.EVENTBUS_USERNAME*/"doom"+':'+/*process.env.EVENTBUS_PASSWORD*/ "machine" +'@'
if (environment == 'development')
{
    rabbitUrl+=EVENTBUS_HOST_DEV || "localhost:5672"
}else
{
    rabbitUrl+=process.env.EVENTBUS_HOST|| "localhost:5672"
}

const subscribe = function (params) {
    var rabbit = jackrabbit(rabbitUrl);
    var exchange = rabbit.fanout();
    var logs = exchange.queue({ exclusive: false });

    logs.consume(onLog, { noAck: true });
    // logs.consume(false); // stops consuming

    function onLog(data) {
        console.log("Received log:", data);
    }
}
module.exports = subscribe
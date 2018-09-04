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
const publish = function(message,channel){
  var rabbit = jackrabbit(rabbitUrl);
  var exchange = rabbit.fanout();

  exchange.publish(message);
  // exchange.on("drain", process.exit);
}
module.exports  = publish;

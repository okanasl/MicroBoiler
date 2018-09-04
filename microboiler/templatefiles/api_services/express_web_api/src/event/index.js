var amqp = require('amqplib/callback_api');

amqp.connect('amqps://doom:machine@localhost',
  opts, function(err, conn) {
    if (err) {
      throw new Error(err)
    }

    console.log(conn)
    conn.close()
})
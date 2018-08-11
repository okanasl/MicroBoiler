var createError = require('http-errors');
var express = require('express');
var cookieParser = require('cookie-parser');
var logger = require('morgan');
//& region (database)
//& region (database:mongodb)
var mongoose   = require('mongoose');
//& region (database:mongodb)
//& region (database)
var bodyParser = require('body-parser');
//& region (database)
//& region (database:mongodb)
var entityRouter = require('./routes/entity');
//& region (database:mongodb)
//& region (database)

//& region (authorization)
var authtestRouter = require('./routes/authtest');
//& region (authorization)

require('dotenv').config()
var environment = process.env.ENVIRONMENT;

var app = express();

app.use(bodyParser.json());
app.use(logger('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());

//& region (database)
//& region (database:mongodb)
app.use('/entity', entityRouter);
//& end (database)
//& end (database:mongodb)
app.use('/authtest', authtestRouter);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  next(createError(404));
});
// configure app to use bodyParser()
// this will let us get the data from a POST
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

var port = process.env.PORT;        // set our port

if (environment == 'Development')
{
  //& region (database)
  //& region (database:mongodb)
  mongoose.connect('mongodb://localhost/test');  
  //& end (database:mongodb)
  //& end (database)
}else{
  //& region (database)
  mongoose.connect('mongodb://MyMongoDb/test');  
  //& end (database)
}
//& region (database)
//& region (database:mongodb)
// Check if we could connect mongodb
mongoose.connection.on('error', console.error.bind(console, `connection error: MongoDb`));
mongoose.connection.once('open', function callback () {
  console.log("Connected To MongoDb Instance");
});
//& end (database:mongodb)
//& end (database)
// error handler
app.use(function(err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  
  res.json({ message: 'Error!',err:err.message, status:err.status });
});

app.listen(port);
console.log('App Listening On Port:' + port);
console.log('App Environment=> '+environment);
module.exports = app;

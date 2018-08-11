
var mongoose     = require('mongoose');
var Schema       = mongoose.Schema;

var EntitySchema   = new Schema({
    name: String,
    description:String
});

module.exports = mongoose.model('Entity', EntitySchema);
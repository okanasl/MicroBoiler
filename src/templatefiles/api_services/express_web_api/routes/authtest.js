var express = require('express');
var router = express.Router();

/* GET users listing. */

router.get('/shouldnotauth', function(req, res) {
  res.json({ message: 'Test Unauthorized Request Success!' });   
});
router.get('/shouldauth', function(req, res) {
  res.json({ message: 'Test Authorized Request Success!' });   
});

module.exports = router;

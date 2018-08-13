var express = require('express');
var router = express.Router();
var auhtorize = require('../middlewares/authorize');

// You can access this route without auth
router.get('/shouldnotauth', function(req, res) {
  res.json({ message: 'Test Unauthorized Request Success!' });   
});
// Use Auth Validtion For This Route
router.use('/shouldauth', auhtorize)
// You cannot access this route without auth
router.get('/shouldauth', (req, res) => {
  res.json({ message: 'Test Authorized Request Success!' });   
});

module.exports = router;

var express = require('express');
var router = express.Router();
var Entity = require('../models/entity');

router.route('/')
    // get all entities
    .get((req,res) =>{
      Entity.find((err, entities) => {
          if (err)
              res.send(err);

          res.json(entities);
      });    
    })
    // create a entity (accessed at POST http://localhost:8080/api/entity)
    .post((req, res) =>{

        var entity = new Entity();      // create a new instance of the Entity model
        entity.name = req.body.name;  // set the entitys name (comes from the request)
        entity.description = req.body.description
        // save the entity and check for errors
        entity.save(function(err) {
            if (err)
                res.send(err);

            res.json({ message: 'Entity created!' });
        });
    });
  router.route('/:entity_id')

    // get single entity
    .get((req, res) =>{
      Entity.findById(req.params.entity_id, function(err, entity) {
        if (err)
            res.send(err);
        res.json(entity);
      });
    })
    // update single entity
    .put((req, res) => {
      Entity.findById(req.params.entity_id, function(err, entity) {

        if (err)
            res.send(err);
        entity.name = req.body.name;
        entity.description = req.body.description;
        entity.save(function(err) {
            if (err)
                res.send(err);

            res.json({ message: 'Entity updated!', });
        });
      })
      // delete single entity
      .delete((req, res) => {
        Entity.remove({
            _id: req.params.entity_id
        }, function(err, entity) {
            if (err)
                res.send(err);

            res.json({ message: 'Successfully deleted Entity', deletedEntity: entity });
        });
    });
});
module.exports = router;

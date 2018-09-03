const Entity = require('../data/models/entity').Entity;
var router = express.Router();

router.route('/')
  .create( (req, res) => {
    return Entity
        .create({
            title: req.body.title,
        })
        .then(entity => res.status(201).send(entity))
        .catch(error => res.send(error));
  })
  .get((req, res) => {
    return Entity
      .all()
      .then(entities => res.status(200).json(entities))
      .catch(error => res.status(200).send(error));
  });
router.route('/:entity_id')
.get( (req, res) => {
    return Entity
        .findById(req.params.entityId)
        .then(entity => {
            if (!entity) {
            return res.status(404).json({
                message: 'Entity Not Found',
            });
            }
            return res.status(200).send(entity);
        })
        .catch(error => res.status(400).send(error));
})
.put( (req, res) => {
    return Entity
        .findById(req.params.entityId)
        .then(entity => {
            if (!entity) {
            return res.status(404).send({
                message: 'Entity Not Found',
            });
            }
            return entity
            .update({
                title: req.body.title || entity.title,
            })
            .then(() => res.status(200).send(entity))  // Send back the updated entity.
            .catch((error) => res.status(400).send(error));
        })
        .catch((error) => res.status(400).send(error));
})
.delete( (req, res) => {
    return Entity
        .findById(req.params.entityId)
        .then(entity => {
            if (!entity) {
            return res.status(400).send({
                message: 'Entity Not Found',
            });
            }
            return entity
                .destroy()
                .then(() => res.status(200).send({ message: 'Entity deleted successfully.' }))
                .catch(error => res.status(400).send(error));
        })
        .catch(error => res.status(400).send(error));
});
module.exports = router;
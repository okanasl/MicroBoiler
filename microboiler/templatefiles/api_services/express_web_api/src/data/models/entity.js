'use strict';
module.exports = (sequelize, DataTypes) => {
  var Entity = sequelize.define('Entity', {
    title: {
      type: DataTypes.STRING,
      allowNull: false,
    },
  }, {});
  Entity.associate = function(models) {
    // associations can be defined here
  };
  return Entity;
};
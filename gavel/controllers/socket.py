from gavel import app
from gavel import socketio
from flask_socketio import emit
from gavel.constants import *
from gavel.models import *
import gavel.settings as settings
import gavel.utils as utils
from sqlalchemy import event
from sqlalchemy import (or_, not_)
from flask import (json)
import asyncio

def standardize(target):
  name = target.__tablename__
  if str(name) == 'annotator':
    return {
      'type': name,
      'target': json.dumps(injectAnnotator(target, target.to_dict()))
    }
  elif str(name) == 'flag':
    return {
      'type': name,
      'target': json.dumps(injectFlag(target, target.to_dict()))
    }
  elif str(name) == 'item':
    return {
      'type': name,
      'target': json.dumps(injectItem(target, target.to_dict()))
    }
  else:
    return {
      'type': name,
      'target': target.to_dict()
    }

def injectAnnotator(target, target_dumped):
  count = Decision.query.filter(Decision.annotator_id == target.id).count()
  target_dumped.update({
    'votes': count
  })

  return target_dumped

def injectFlag(target, target_dumped):
  target_dumped.update({
    'item_name': target.item.name,
    'item_location': target.item.location,
    'annotator_name': target.annotator.name
  })
  return target_dumped

def injectItem(target, target_dumped):
  assigned = Annotator.query.filter(Annotator.next == target).all()
  viewed_ids = {i.id for i in target.viewed}
  if viewed_ids:
    skipped = Annotator.query.filter(
      Annotator.ignore.contains(target) & ~Annotator.id.in_(viewed_ids)
    ).count()
  else:
    skipped = Annotator.query.filter(Annotator.ignore.contains(target)).count()

  viewed = len(target.viewed)

  target_dumped.update({
    'viewed': viewed,
    'votes': Decision.query.filter(or_(Decision.winner_id == target.id, Decision.loser_id == target.id)).distinct(Decision.id).count(),
    'skipped': skipped
  })
  return target_dumped

CONNECT = 'connected'

ANNOTATOR_INSERTED = 'annotator.inserted'
ANNOTATOR_UPDATED = 'annotator.updated'

ITEM_INSERTED = 'item.inserted'
ITEM_UPDATED = 'item.updated'

FLAG_INSERTED = 'flag.inserted'
FLAG_UPDATED = 'flag.updated'

SETTING_INSERTED = 'setting.inserted'
SETTING_UPDATED = 'setting.updated'

@socketio.on('user.connected', namespace='/admin')
def test_connect(data):
  emit(CONNECT, data, namespace='/admin')

@socketio.on('annotator.updated.confirmed', namespace='/admin')
@utils.requires_auth
def triggerRelatedItemUpdates(data):
  try:
    ignore_ids = {i['id'] for i in data['ignore']}
    items = Item.query.filter(Item.id.in_(ignore_ids))
    for i in items:
      socketio.emit(DB_MODIFY_EVENT, standardize(i), namespace='/admin')
  except Exception as e:
    return

@event.listens_for(Annotator, 'after_insert')
@utils.requires_auth
def annotator_listen_insert(mapper, connection, target):
  socketio.emit(ANNOTATOR_INSERTED, standardize(target), namespace='/admin')

@event.listens_for(Annotator, 'after_update')
@utils.requires_auth
def annotator_listen_modify(mapper, connection, target):
  socketio.emit(ANNOTATOR_UPDATED, standardize(target), namespace='/admin')

@event.listens_for(Item, 'after_insert')
@utils.requires_auth
def item_listen_insert(mapper, connection, target):
  socketio.emit(ITEM_INSERTED, standardize(target), namespace='/admin')

@event.listens_for(Item, 'after_update')
@utils.requires_auth
def item_listen_modify(mapper, connection, target):
  socketio.emit(ITEM_UPDATED, standardize(target), namespace='/admin')

@event.listens_for(Flag, 'after_insert')
@utils.requires_auth
def flag_listen_insert(mapper, connection, target):
  socketio.emit(FLAG_INSERTED, standardize(target), namespace='/admin')

@event.listens_for(Flag, 'after_update')
@utils.requires_auth
def flag_listen_update(mapper, connection, target):
  socketio.emit(FLAG_UPDATED, standardize(target), namespace='/admin')

@event.listens_for(Setting, 'after_insert')
@utils.requires_auth
def setting_listen_insert(mapper, connection, target):
  socketio.emit(SETTING_INSERTED, standardize(target), namespace='/admin')

@event.listens_for(Setting, 'after_update')
@utils.requires_auth
def setting_listen_update(mapper, connection, target):
  socketio.emit(SETTING_UPDATED, standardize(target), namespace='/admin')
import signal
import os
import time
import urllib
import random

from simplejson import dumps as to_json
from simplejson import loads as from_json

from webgui import start_gtk_thread
from webgui import launch_browser
from webgui import synchronous_gtk_message
from webgui import asynchronous_gtk_message
from webgui import kill_gtk_thread

import sqlite3 as lite
import sys

class Global(object):
    quit = False
    @classmethod
    def set_quit(cls, *args, **kwargs):
        cls.quit = True


def main():
    start_gtk_thread()

    # Location of data (db + blobs)
    location = urllib.pathname2url(os.path.abspath("../data/"))

    # Create a proper file:// URL pointing to the ui:
    file = os.path.abspath('../ui/index.html')
    uri = 'file://' + urllib.pathname2url(file)
    browser, web_recv, web_send = \
        synchronous_gtk_message(launch_browser)(uri,
                                                quit_function=Global.set_quit)

    # Finally, here is our personalized main loop, 100% friendly
    # with "select" (although I am not using select here)!:
    last_second = time.time()
    uptime_seconds = 1
    clicks = 0

    dbname = location + "/notes.db"

    # listen for updates
    while not Global.quit:

        current_time = time.time()
        again = False
        msg = web_recv()
        if msg:
            msg = from_json(msg)
            again = True

        if msg != None:
            if msg['type'] == "document-ready":
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()    
                    cur.execute("DELETE FROM tree_entity WHERE is_deleted=1")
                    con.commit()
                    cur.execute("DELETE FROM list_item WHERE is_deleted=1")
                    con.commit()
                    cur.execute("DELETE FROM blob WHERE is_deleted=1")
                    con.commit()
                    cur.execute("SELECT * FROM tree_entity WHERE is_deleted=0 AND is_archived=0 ORDER BY order_in_parent ASC")

                    rows = cur.fetchall()
 
                    to = 1
                    for row in rows:
                        colour = "white"
                        if row['color_name'] == "RED":
                            colour = "red"
                        if row['color_name'] == "ORANGE":
                            colour = "orange"
                        if row['color_name'] == "YELLOW":
                            colour = "yellow"
                        if row['color_name'] == "GRAY":
                            colour = "grey"
                        if row['color_name'] == "BLUE":
                            colour = "cyan"
                        if row['color_name'] == "TEAL":
                            colour = "turq"
                        if row['color_name'] == "GREEN":
                            colour = "lime"

                        # go through blobs to see if we have an associated image
                        cur.execute("SELECT * FROM blob WHERE tree_entity_id = %d AND is_deleted=0 ORDER BY time_last_updated DESC LIMIT 1" % row['_id'])
                        rows2 = cur.fetchall()
                        img = ""
                        for row2 in rows2:
                            tpe="image"
                            if row2['mime_type'].startswith("audio"):
                                tpe="audio"
                            fname = location + "/blob/"+tpe+"/original/"+row2['file_name']
                            img="data:"+row2['mime_type']+";base64,"+urllib.quote(open(fname, "rb").read().encode("base64"))

                        if row['type'] == 0: # text item   
                            cur.execute("SELECT * FROM list_item WHERE list_parent_id = %d AND is_deleted=0 ORDER BY order_in_parent ASC" % row['_id'])
                            rows2 = cur.fetchall()
                            txtxt=""
                            for row2 in rows2:
                                txtxt=row2['text'].replace('"', '\\"').replace('\n', '\\n')
                            web_send("setTimeout(function () { addcardText(\"%s\", \"%s\", \"%s\", 0, %d, \"%s\", \"%s\"); }, %d);" % (row['uuid'], row['title'], txtxt, row['time_last_updated'], colour, img, to))
                        else: # list
                            listcont = ""
                            cur.execute("SELECT * FROM list_item WHERE list_parent_id = %d AND is_deleted=0 ORDER BY order_in_parent ASC" % row['_id'])
                            rows2 = cur.fetchall()
                            for row2 in rows2:
                                if row2['is_checked'] == 1:
                                    listcont += "[x] "
                                else:
                                    listcont += "[ ] "
                                listcont += (row2['uuid'])+"| "+row2['text'].replace('\n', '\\n')+"\\n"
                            web_send("setTimeout(function () { addcardText(\"%s\", \"%s\", \"%s\", 1, %d, \"%s\", \"%s\"); }, %d);" % (row['uuid'], row['title'], listcont.replace('"', '\\"'), row['time_last_updated'], colour, img, to))
                        to += 10
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()
            if msg['type'] == "ins-note":
                # add new note
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()
                    # update note
                    cur.execute("SELECT _id FROM tree_entity ORDER BY _id DESC LIMIT 1")
                    rows2 = cur.fetchall()
                    _id=""
                    for row2 in rows2:
                        _id=row2['_id']+1
                    ran=0
                    while ran < _id:
                        ran = random.randint(1,1000)
                    _id=ran
                    

                    cur.execute("SELECT order_in_parent FROM tree_entity ORDER BY order_in_parent DESC LIMIT 1")
                    rows2 = cur.fetchall()
                    oip=""
                    for row2 in rows2:
                        oip=row2['order_in_parent']+1

                    colour = ""
                    if msg['col'] == "red":
                        colour = "RED"
                    if msg['col'] == "orange":
                        colour = "ORANGE"
                    if msg['col'] == "yellow":
                        colour = "YELLOW"
                    if msg['col'] == "grey":
                        colour = "GRAY"
                    if msg['col'] == "cyan":
                        colour = "BLUE"
                    if msg['col'] == "turq":
                        colour = "TEAL"
                    if msg['col'] == "lime":
                        colour = "GREEN"
                    cur.execute("INSERT INTO tree_entity(_id, account_id, uuid, type, title, color_name, order_in_parent, time_created, time_last_updated) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)", (_id, msg['uid'], msg['typ'], msg['title'], colour, oip, msg['dt'], msg['dt']))
                    con.commit()

                    if msg['img']:
                        fname = msg['uid']
                        # write file
                        bits=msg['img'].split(';base64,', 1)
                        path = location + "/blob/image/original/"+fname
                        fh = open(path, "wb")
                        fh.write(urllib.unquote(bits[1]).decode('utf8').decode('base64'))
                        fh.close()

                        cur.execute("INSERT INTO blob(account_id, uuid, type, mime_type, tree_entity_id, file_name, blob_size, time_created, time_last_updated) VALUES (1, ?, 0, ?, ?, ?, ?, ?, ?)", (msg['uid'], bits[0].split(":", 1)[1], _id, fname, os.stat(path).st_size, msg['dt'], msg['dt']))
                        con.commit()

                    if msg['typ'] == 0:
                        cur.execute("INSERT INTO list_item(account_id, uuid, text, time_created, time_last_updated, list_parent_id) VALUES (1, ?, ?, ?, ?, ?)", (msg['uid'], msg['text'], msg['dt'], msg['dt'], _id))
                        con.commit()
                    if msg['typ'] == 1:
                        listitems = msg['text'].split('\n')
                        ordr=0
                        for line in listitems:
                            if(line==''):
                                continue
                            lbits = line.split('] ')
                            checked=0
                            if(lbits[0] == '[ '):
                                checked = 0
                            else:
                                checked = 1
                            lbits = lbits[1].split('|', 1)
                            uuid=lbits[0]
                            txtxt=lbits[1]
                            cur.execute("INSERT INTO list_item(account_id, uuid, text, list_parent_id, order_in_parent, is_checked, time_created, time_last_updated) VALUES (1, ?, ?, ?, ?, ?, ?, ?)", (uuid, txtxt, _id, ordr, checked, msg['dt'], msg['dt']))
                            con.commit()
                            ordr+=1
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()

            if msg['type'] == "upd-note":
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()
                    # update note
                    cur.execute("SELECT * FROM tree_entity WHERE uuid = ?" , (msg['uid'],))
                    rows2 = cur.fetchall()
                    _id=""
                    oip=""
                    tc=""
                    for row2 in rows2:
                        _id=row2['_id']
                        oip=row2['order_in_parent']
                        tc=row2['time_created']

                    cur.execute("SELECT * FROM blob WHERE tree_entity_id = ?" , (_id,))
                    rows2 = cur.fetchall()
                    fname=""
                    for row2 in rows2:
                        fname=row2['file_name']
                    cur.execute("DELETE FROM tree_entity WHERE _id=?", (_id,))
                    con.commit()
                    cur.execute("DELETE FROM list_item WHERE list_parent_id=?", (_id,))
                    con.commit()
                    cur.execute("DELETE FROM blob WHERE tree_entity_id=?", (_id,))
                    con.commit()

                    colour = ""
                    if msg['col'] == "red":
                        colour = "RED"
                    if msg['col'] == "orange":
                        colour = "ORANGE"
                    if msg['col'] == "yellow":
                        colour = "YELLOW"
                    if msg['col'] == "grey":
                        colour = "GRAY"
                    if msg['col'] == "cyan":
                        colour = "BLUE"
                    if msg['col'] == "turq":
                        colour = "TEAL"
                    if msg['col'] == "lime":
                        colour = "GREEN"
                    cur.execute("INSERT INTO tree_entity(_id, account_id, uuid, type, title, color_name, order_in_parent, time_created, time_last_updated) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)", (_id, msg['uid'], msg['typ'], msg['title'], colour, oip, tc, msg['dt']))
                    con.commit()

                    if msg['img']:
                        if not fname:
                            fname = msg['uid']
                        # write file
                        bits=msg['img'].split(';base64,', 1)
                        path = location + "/blob/image/original/"+fname
                        fh = open(path, "wb")
                        fh.write(urllib.unquote(bits[1]).decode('utf8').decode('base64'))
                        fh.close()

                        cur.execute("INSERT INTO blob(account_id, uuid, type, mime_type, tree_entity_id, file_name, blob_size, time_created, time_last_updated) VALUES (1, ?, 0, ?, ?, ?, ?, ?, ?)", (msg['uid'], bits[0].split(":", 1)[1], _id, fname, os.stat(path).st_size, tc, msg['dt']))
                        con.commit()

                    if msg['typ'] == 0:
                        cur.execute("INSERT INTO list_item(account_id, uuid, text, time_created, time_last_updated, list_parent_id) VALUES (1, ?, ?, ?, ?, ?)", (msg['uid'], msg['text'], tc, msg['dt'], _id))
                        con.commit()
                    if msg['typ'] == 1:
                        listitems = msg['text'].split('\n')
                        ordr=0
                        for line in listitems:
                            if(line==''):
                                continue
                            lbits = line.split('] ')
                            checked=0
                            if(lbits[0] == '[ '):
                                checked = 0
                            else:
                                checked = 1
                            lbits = lbits[1].split('|', 1)
                            uuid=lbits[0]
                            txtxt=lbits[1]
                            cur.execute("INSERT INTO list_item(account_id, uuid, text, list_parent_id, order_in_parent, is_checked, time_created, time_last_updated) VALUES (1, ?, ?, ?, ?, ?, ?, ?)", (uuid, txtxt, _id, ordr, checked, tc, msg['dt']))
                            con.commit()
                            ordr+=1
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()

            if msg['type'] == "del-note":
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()
                    # update note
                    cur.execute("SELECT * FROM tree_entity WHERE uuid = ?" , (msg['uid'],))
                    rows2 = cur.fetchall()
                    _id=""
                    for row2 in rows2:
                        _id=row2['_id']

                    cur.execute("DELETE FROM tree_entity WHERE _id=?", (_id,))
                    con.commit()
                    cur.execute("DELETE FROM list_item WHERE list_parent_id=?", (_id,))
                    con.commit()
                    cur.execute("DELETE FROM blob WHERE tree_entity_id=?", (_id,))
                    con.commit()
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()

            if msg['type'] == "arc-note":
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()
                    # update note
                    cur.execute("SELECT * FROM tree_entity WHERE uuid = ?" , (msg['uid'],))
                    rows2 = cur.fetchall()
                    _id=""
                    for row2 in rows2:
                        _id=row2['_id']

                    cur.execute("UPDATE tree_entity SET is_archived=1 WHERE _id=?", (_id,))
                    con.commit()
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()
            if msg['type'] == "unarc-note":
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()
                    # update note
                    cur.execute("SELECT * FROM tree_entity WHERE uuid = ?" , (msg['uid'],))
                    rows2 = cur.fetchall()
                    _id=""
                    for row2 in rows2:
                        _id=row2['_id']

                    cur.execute("UPDATE tree_entity SET is_archived=0 WHERE _id=?", (_id,))
                    con.commit()
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()

            if msg['type'] == "show-arc":
                try:
                    con = lite.connect(dbname)
                    con.row_factory = lite.Row 
                    cur = con.cursor()
                    cur.execute("SELECT * FROM tree_entity WHERE is_deleted=0 AND is_archived=1 ORDER BY order_in_parent ASC")

                    rows = cur.fetchall()
 
                    to = 1
                    for row in rows:
                        colour = "white"
                        if row['color_name'] == "RED":
                            colour = "red"
                        if row['color_name'] == "ORANGE":
                            colour = "orange"
                        if row['color_name'] == "YELLOW":
                            colour = "yellow"
                        if row['color_name'] == "GRAY":
                            colour = "grey"
                        if row['color_name'] == "BLUE":
                            colour = "cyan"
                        if row['color_name'] == "TEAL":
                            colour = "turq"
                        if row['color_name'] == "GREEN":
                            colour = "lime"

                        # go through blobs to see if we have an associated image
                        cur.execute("SELECT * FROM blob WHERE tree_entity_id = %d AND is_deleted=0 ORDER BY time_last_updated DESC LIMIT 1" % row['_id'])
                        rows2 = cur.fetchall()
                        img = ""
                        for row2 in rows2:
                            tpe="image"
                            if row2['mime_type'].startswith("audio"):
                                tpe="audio"
                            fname = location + "/blob/"+tpe+"/original/"+row2['file_name']
                            img="data:"+row2['mime_type']+";base64,"+urllib.quote(open(fname, "rb").read().encode("base64"))

                        if row['type'] == 0: # text item   
                            cur.execute("SELECT * FROM list_item WHERE list_parent_id = %d AND is_deleted=0 ORDER BY order_in_parent ASC" % row['_id'])
                            rows2 = cur.fetchall()
                            txtxt=""
                            for row2 in rows2:
                                txtxt=row2['text'].replace('"', '\\"').replace('\n', '\\n')
                            web_send("setTimeout(function () { addcardText(\"%s\", \"%s\", \"%s\", 0, %d, \"%s\", \"%s\"); }, %d);" % (row['uuid'], row['title'], txtxt, row['time_last_updated'], colour, img, to))
                        else: # list
                            listcont = ""
                            cur.execute("SELECT * FROM list_item WHERE list_parent_id = %d AND is_deleted=0 ORDER BY order_in_parent ASC" % row['_id'])
                            rows2 = cur.fetchall()
                            for row2 in rows2:
                                if row2['is_checked'] == 1:
                                    listcont += "[x] "
                                else:
                                    listcont += "[ ] "
                                listcont += (row2['uuid'])+"| "+row2['text'].replace('\n', '\\n')+"\\n"
                            web_send("setTimeout(function () { addcardText(\"%s\", \"%s\", \"%s\", 1, %d, \"%s\", \"%s\"); }, %d);" % (row['uuid'], row['title'], listcont.replace('"', '\\"'), row['time_last_updated'], colour, img, to))
                        to += 10
                except lite.Error, e:
                    print "Error %s:" % e.args[0]
                    sys.exit(1)
                finally:
                    if con:
                        con.close()

        if again: pass
        else:     time.sleep(0.1)


def my_quit_wrapper(fun):
    signal.signal(signal.SIGINT, Global.set_quit)
    def fun2(*args, **kwargs):
        try:
            x = fun(*args, **kwargs) # equivalent to "apply"
        finally:
            kill_gtk_thread()
            Global.set_quit()
        return x
    return fun2

if __name__ == '__main__':
    my_quit_wrapper(main)()

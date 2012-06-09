import sys
import re
import sqlite3
from standardize import name_standardize

# actually store the data
store = True

# open db
db_fname = 'store/patents.db'
conn = sqlite3.connect(db_fname)
cur = conn.cursor()
cur_same = conn.cursor()
cmd_same = 'update assignment set same_flag=? where rowid=?'

# create flag tables
try:
  cur.execute('alter table assignment add column same_flag int default 0')
try:
  cur.execute('alter table assignment add column dup_flag int default 0')
try:
  cur.execute('alter table assignment add column use_flag int default 0')

batch_size = 1000
same_flags = []

rlim = sys.maxint
match_num = 0
rnum = 0
for row in cur.execute('select rowid,patnum,assignor,assignee,conveyance from assignment'):
  (rowid,patnum,assignor,assignee,conveyance) = row

  assignor_toks = name_standardize(assignor)
  assignee_toks = name_standardize(assignee)

  word_match = 0
  for tok in assignor_toks:
    if tok in assignee_toks:
      word_match += 1

  word_match /= max(1.0,0.5*(len(assignor_toks)+len(assignee_toks)))
  match = word_match > 0.5

  #if match:
  #  print '{:7}-{:7}, {:10.3}: {:50.50} -> {:50.50}'.format(rowid,patnum,word_match,','.join(assignor_toks),','.join(assignee_toks))

  if store:
    same_flags.append((match,rowid))
    if len(same_flags) >= batch_size:
      cur_same.executemany(cmd_same,same_flags)
      del same_flags[:]

  match_num += match

  rnum += 1
  if rnum >= rlim:
    break

  if rnum%50000 == 0:
    print rnum

if store:
  # clean up
  if len(same_flags) > 0:
    cur_same.executemany(cmd_same,same_flags)

  # flag duplicate entries (dup_flag)
  #cur.execute('drop table if exists assign_dups')
  #cur.execute('create table assign_dups as select patnum,execdate,max(same_flag) from assignment group by patnum,execdate having count(*)>1')
  #cur.execute('create unique index assign_dups_idx on assign_dups (patnum,execdate)')
  #cur.execute('update assignment set dup_flag=1 where rowid in (select assignment.rowid from assignment,assign_dups where assignment.patnum = assign_dups.patnum and assignment.execdate = assign_dups.execdate)')
  #cur.execute('drop table assign_dups')

  # use the first entry that doesn't have same_flag=1
  cur.execute('update assignment set use_flag=1 where rowid in (select min(rowid) from assignment group by patnum,execdate,same_flag) and same_flag=0')
  cur.execute('create table assignment_use as select * from assignment where use_flag=1')
  cur.execute('create unique index assign_idx on assignment_use(patnum,execdate)')

  # commit changes
  conn.commit()

# close db
conn.close()

print match_num
print rnum
print rnum-match_num
print float(match_num)/float(rnum)

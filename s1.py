import sqlalchemy

engine =  sqlalchemy.create_engine("sqlite:///x.sqlite", echo=True)

md = sqlalchemy.MetaData(bind=engine)

conn = sqlalchemy.engine.base.Connection(engine)

conn.execute("create table x (col1 sxtring(50), col2 string(50))")

x = sqlalchemy.Table("x", md)

ins = x.insert().execute(col1="val11", col2="val12")
#.values( col1="val11", col2="val12")

print str(ins)

#conn.execute(ins, col1="val11", col2="val12")

rs = conn.execute("select * from x")

rows = rs.fetchall()


for r in rows:
  print r

rs.close()
conn.close()

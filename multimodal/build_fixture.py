"""Create a clearly labeled fictional report for reproducible page-retrieval tests."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parents[1]

def build():
 path=ROOT/'fixtures/fictional-operations.pdf'
 c=canvas.Canvas(str(path),pagesize=(612,792))
 def header(title,page):
  c.setFillColor(HexColor('#14241e'));c.rect(0,0,612,792,fill=1,stroke=0)
  c.setFillColor(HexColor('#c8f580'));c.setFont('Helvetica',11);c.drawString(48,742,'NORTHSTAR / FICTIONAL OPERATIONS REPORT')
  c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica-Bold',25);c.drawString(48,680,title)
  c.setFont('Helvetica',10);c.drawString(48,45,f'Synthetic demonstration. No real company data. | Page {page}')
 def line(text,y):
  c.setFillColor(HexColor('#e4ede5'));c.setFont('Helvetica',12);c.drawString(48,y,text)
 header('Regional delivery performance',1)
 line('Table 1. On-time delivery rate by region',625)
 rows=[['Region','Orders','On-time rate'],['North','1,200','94%'],['South','950','88%'],['West','1,450','97%']]
 for i,row in enumerate(rows):
  y=565-i*48
  for x,text in zip([65,240,410],row):c.drawString(x,y,text)
 for y in [594,546,498,450,402]:
  c.setStrokeColor(HexColor('#7b9981'));c.line(48,y,564,y)
 for x in [48,220,390,564]:c.line(x,402,x,594)
 line('West had the highest on-time rate at 97%.',330)
 line('South had the lowest on-time rate at 88%.',304)
 c.showPage();header('Monthly energy consumption',2)
 line('Figure 1. Electricity usage in MWh',625)
 values=[40,55,70,50];labels=['January','February','March','April']
 for i,(v,label) in enumerate(zip(values,labels)):
  x=80+i*125;c.setFillColor(HexColor('#c8f580'));c.rect(x,280,64,v*3,fill=1,stroke=0)
  c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica',12);c.drawString(x+12,290+v*3,str(v));c.drawString(x-3,250,label)
 line('March was the peak month, consuming 70 MWh.',195)
 line('April usage decreased to 50 MWh.',170)
 c.showPage();header('Incident response policy',3)
 for text,y in [('Severity-one alerts require acknowledgment within 15 minutes.',620),('The incident commander publishes updates every 30 minutes.',585),('Recovery exercises are scheduled once per quarter.',550),('Application logs are retained for 30 days.',515)]:line(text,y)
 c.showPage();c.save();print(path)
if __name__=='__main__':build()

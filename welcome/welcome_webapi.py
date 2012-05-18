import webapp2
from reportlab.pdfgen import canvas

class MainPage(webapp2.RequestHandler):

  def get(self):

    self.response.headers['Content-Type']  = "application/pdf"
    self.response.headers['Content-Disposition']  = "attachment; filename=somefilename.pdf"
    p = canvas.Canvas(self.response)
    p.drawString(100, 100, "Hello world.")
    p.showPage()
    p.save()

application = webapp2.WSGIApplication(
   [
    ('/', MainPage),
   ] , debug=True)

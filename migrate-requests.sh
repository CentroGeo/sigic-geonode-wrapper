# crea las migraciones de la app sigic_request 
python manage.py makemigrations sigic_request

# pasa las migraciones creadas a la BD
python manage.py migrate

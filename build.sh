#!/usr/bin/env bash
# Script de build que corre Render en cada deploy.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Collectstatic agrupa los estáticos para que WhiteNoise los sirva.
python manage.py collectstatic --no-input

# Migraciones: sólo auth, sessions y axes. El modelo RegistroMovimiento tiene
# managed=False, así que Django no intenta tocar la tabla de Supabase.
python manage.py migrate --no-input

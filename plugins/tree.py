# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 Stéphane Graber
# Author: Stéphane Graber <stgraber@ubuntu.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You can find the license on Debian systems in the file
# /usr/share/common-licenses/GPL-2

from libs.common import iri_for as url_for
from flask import g, render_template, request, redirect
from libs.ldap_func import ldap_auth, ldap_get_entries, ldap_in_group
from flask_wtf import FlaskForm
from wtforms import StringField


TREE_BLACKLIST = ["CN=ForeignSecurityPrincipals",
                  "OU=sudoers"]

class FilterTreeView(FlaskForm):
    filter_str = StringField('Buscar')


def init(app):
    @app.route('/tree', methods=['GET', 'POST'] )
    @app.route('/tree/<base>', methods=['GET', 'POST'])
    @ldap_auth("SM Admin")
    
    def tree_base(base=None):

        if not base:
            base = g.ldap['dn']
        elif not base.lower().endswith(g.ldap['dn'].lower()):
            base += ",%s" % g.ldap['dn']

        admin = ldap_in_group("SM Admin")
        entry_fields = [('name', "Nombre"),
                        ('__description', u"Login/Descripción"),
                        ('__type', "Tipo"),
                        ('active', "Estado")]

        form = FilterTreeView(request.form)

        if form.validate_on_submit():
            filter_str = form.filter_str.data
            scope = "subtree"
        else:
            filter_str = None
            form.filter_str.data = u'Buscar'
            scope = "onelevel"

        entries = []
        users = sorted(ldap_get_entries("objectClass=person", base, scope, ignore_erros=False), key=lambda entry: entry['displayName'])
        other_entries = sorted(ldap_get_entries("objectClass=top", base, scope, ignore_erros=False), key=lambda entry: entry['name'])

        for entry in users:
            if 'description' not in entry:
                if 'sAMAccountName' in entry:
                   entry['__description'] = entry['sAMAccountName']
            else:
                entry['__description'] = entry['description']

            entry['__target'] = url_for('tree_base',
                                        base=entry['distinguishedName'])
            if 'user' in entry['objectClass']:
                try:
                    entry['name'] = entry['displayName']
                except:
                    entry['name'] = entry['cn']
                entry['__type'] = "Usuario"
                entry['__target'] = url_for('user_overview',
                                            username=entry['sAMAccountName'])
            
            if 'user' in entry['objectClass']:
                if entry['userAccountControl'] == 512:
                    entry['active'] = "Activo"
                else:
                    entry['active'] = "Desactivado"
            else:
                entry['active'] = "No disponible"

            if 'showInAdvancedViewOnly' in entry \
               and entry['showInAdvancedViewOnly']:
                continue

            for blacklist in TREE_BLACKLIST:
                if entry['distinguishedName'].startswith(blacklist):
                    break

            if filter_str:
                if '__description' in entry and filter_str in entry['__description'].lower():
                    entries.append(entry)
                elif 'sAMAccountName' in entry and filter_str in entry['sAMAccountName'].lower():
                    entries.append(entry)
            else:
                entries.append(entry)
        
        for entry in other_entries:
            if entry not in users:
                if 'description' not in entry:
                    if 'sAMAccountName' in entry:
                        entry['__description'] = entry['sAMAccountName']
                else:
                    entry['__description'] = entry['description']
                
                entry['__target'] = url_for('tree_base',
                                        base=entry['distinguishedName'])

                if 'group' in entry['objectClass']:
                    entry['__type'] = "Grupo"
                    entry['__target'] = url_for('group_overview',
                                                groupname=entry['sAMAccountName'])
                elif 'organizationalUnit' in entry['objectClass']:
                    entry['__type'] = "Unidad Organizativa"
                elif 'container' in entry['objectClass']:
                    entry['__type'] = "Contenedor"
                elif 'builtinDomain' in entry['objectClass']:
                    entry['__type'] = "Built-in"
                else:
                    entry['__type'] = "Desconocido"

                if filter_str:
                    if '__description' in entry and filter_str in entry['__description'].lower():
                        entries.append(entry)
                    elif 'sAMAccountName' in entry and filter_str in entry['sAMAccountName'].lower():
                        entries.append(entry)
                else:
                    entries.append(entry)

        parent = None
        base_split = base.split(',')
        if not base_split[0].lower().startswith("dc"):
            parent = ",".join(base_split[1:])

        return render_template("pages/tree_base_es.html", form=form, parent=parent,
                               admin=admin, base=base, entries=entries,
                               entry_fields=entry_fields)

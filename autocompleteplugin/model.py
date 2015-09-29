# coding: utf-8
#
# Copyright (c) 2010, Logica
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------
from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.db.schema import Table, Column
from trac.config import ListOption
from tracsqlhelper import execute_non_query, get_scalar, create_table

class AutoCompleteModel(Component):
    implements(IEnvironmentSetupParticipant)
    
    #Default values, read from trac.ini on creation
    _default_autocomplete_values = ListOption('autocomplete', 'shown_groups',
                               'project_viewers,project_managers,project_members', doc=
                               """User groups used in auto complete enabled inputs.""")

    _default_autocomplete_name = _default_autocomplete_values.name
    _default_autocomplete_description = _default_autocomplete_values.__doc__

    #IEnvironmentSetupParticipant methods
    def environment_created(self):
        """Called when a new Trac environment is created."""
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        """Called when Trac checks whether the environment needs to be upgraded.
        
        Should return `True` if this participant needs an upgrade to be
        performed, `False` otherwise.
        """
        version = self.version()
        return version < len(self.steps)

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade.
        
        Implementations of this method don't need to commit any database
        transactions. This is done implicitly for each participant
        if the upgrade succeeds without an error being raised.

        However, if the `upgrade_environment` consists of small, restartable,
        steps of upgrade, it can decide to commit on its own after each
        successful step.
        """
        if not self.environment_needs_upgrade(db):
            return

        version = self.version()
        for version in range(self.version(), len(self.steps)):
            for step in self.steps[version]:
                step(self)
        execute_non_query(self.env, """UPDATE SYSTEM SET value='%s' WHERE 
                    name='autocompleteplugin.db_version';""" % len(self.steps))
        
    def version(self):
        """Returns version of the database (an int)"""
        version = get_scalar(self.env, """SELECT value FROM system WHERE name = 
                                        'autocompleteplugin.db_version';""")
        if version:
            return int(version)
        return 0
    
    ### upgrade steps

    def create_db(self):
        autocomplete_table = Table('autocomplete', key='name')[ 
                                Column('name', 'text'),
                                Column('description', 'text')]
        autocomplete_values_table = Table('autocomplete_values')[
                                Column('autocomplete_name', 'text'), 
                                Column('value', 'text')]

        create_table(self.env, autocomplete_table)
        create_table(self.env, autocomplete_values_table)
        execute_non_query(self.env, """INSERT INTO system (name, value) VALUES 
                                    ('autocompleteplugin.db_version', '1');""")
        
    def add_default_data(self):
        #Add default autocomplete name
        AutoCompleteGroup(self.env).add_autocomplete(self._default_autocomplete_name, 
                                                     self._default_autocomplete_description)
        #Add default autocomplete names
        for value in self._default_autocomplete_values:
            AutoCompleteGroup(self.env).add_autocomplete_name(self._default_autocomplete_name, 
                                                              value)
            
    def remove_data_from_config(self):
        #Remove shown_groups from config
        self.config.set('autocomplete', 'shown_groups', None)
        self.config.save()
    
    # ordered steps for upgrading
    steps = [ [ create_db, add_default_data, remove_data_from_config ] # version 1
            ]

class AutoCompleteGroup(object):
    """Simple class for handling AutoComplete group values"""

    def __init__(self, env):
        self.env = env
    
    def get_autocomplete_values(self, autocomplete_name):
        """Returns a list of values for the given autocomplete_name"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute('SELECT value FROM autocomplete_values WHERE autocomplete_name = %s',
                       (autocomplete_name,))
        values = [value for value, in cursor]
        return values
    
    def add_autocomplete(self, autocomplete_name, description=None):
        """Adds an autocomplete section with description"""
        db = self.env.get_db_cnx()
        
        if not description:
            description = ""
        @self.env.with_transaction()
        def do_save(db):
            cursor = db.cursor()
            cursor.execute('''INSERT INTO autocomplete(name, description) VALUES 
                            (%s, %s)''',(autocomplete_name, description))
        
    def add_autocomplete_name(self, autocomplete_name, value):
        """Adds an autocomplete value related to an autocomplete name"""
        db = self.env.get_db_cnx()
        
        relation_exists = self.check_if_section_name_exists(autocomplete_name, value)

        @self.env.with_transaction()
        def do_save(db):
            cursor = db.cursor()
            #Add data only if no relation exists
            if not relation_exists:
                cursor.execute('''INSERT INTO autocomplete_values(autocomplete_name, 
                                value) VALUES (%s, %s)''',(autocomplete_name, value))
            
    def remove_autocomplete_name(self, autocomplete_name, value):
        """Remove an autocomplete value related to an autocomplete name"""
        db = self.env.get_db_cnx()
        
        relation_exists = self.check_if_section_name_exists(autocomplete_name, value)

        @self.env.with_transaction()
        def do_delete(db):
            #Remove only if relation exists
            if relation_exists:
                cursor = db.cursor()
                cursor.execute('''DELETE FROM autocomplete_values WHERE 
                                autocomplete_name = %s AND value = %s''', 
                                (autocomplete_name, value))
    
    def check_if_section_name_exists(self, autocomplete_name, value):
        """Checks if autocomplete_name name relation exists"""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        cursor.execute('''SELECT autocomplete_name FROM autocomplete_values WHERE
                        autocomplete_name = %s AND value = %s''', 
                        (autocomplete_name, value,))
    
        if cursor.fetchone() is None:
            return False
        return True

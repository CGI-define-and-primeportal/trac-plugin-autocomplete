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
from trac.db.api import DatabaseManager
from trac.config import ListOption

class AutoCompleteModel(Component):
    implements(IEnvironmentSetupParticipant)
    
    #Default values, read from trac.ini on creation
    _default_autocomplete_values = ListOption('autocomplete', 'shown_groups',
                               'project_managers,project_viewers,external_developers', doc=
                               """User groups used in auto complete enabled inputs.""")

    _default_autocomplete_name = _default_autocomplete_values.name
    _default_autocomplete_description = _default_autocomplete_values.__doc__

    _autocomplete_schemas = [Table('autocomplete', key='name')[ 
                                Column('name', 'text'),
                                Column('description', 'text')],
                             Table('autocomplete_values')[
                                Column('autocomplete_name', 'text'), 
                                Column('value', 'text')]]

    #IEnvironmentSetupParticipant methods
    def environment_created(self):
        """Called when a new Trac environment is created."""
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        """Called when Trac checks whether the environment needs to be upgraded.
        
        Should return `True` if this participant needs an upgrade to be
        performed, `False` otherwise.
        """
        autocomplete_tables = ['autocomplete', 'autocomplete_values']
        
        try:
            @self.env.with_transaction()
            def check(db):
                cursor = db.cursor()
                for table_name in autocomplete_tables:
                    sql = 'SELECT * FROM %s' % table_name
                    cursor.execute(sql)
                    cursor.fetchone()
        except Exception, ex:
            self.log.debug('''Upgrade of schema needed for AutoComplete plugin''', 
                           exc_info=True)
            return True
        
        return False

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade.
        
        Implementations of this method don't need to commit any database
        transactions. This is done implicitly for each participant
        if the upgrade succeeds without an error being raised.

        However, if the `upgrade_environment` consists of small, restartable,
        steps of upgrade, it can decide to commit on its own after each
        successful step.
        """        
        self.log.debug('Upgrading schema for AutoComplete plugin')
        connector = DatabaseManager(self.env).get_connector()[0]
        cursor = db.cursor()

        for table in self._autocomplete_schemas:
            for stmt in connector.to_sql(table):
                self.log.debug(stmt)
                try:
                    cursor.execute(stmt)
                    #Add default autocomplete name
                    if table.name == 'autocomplete':
                        add_autocomplete(self.env, self._default_autocomplete_name, 
                                         self._default_autocomplete_description)
                    #Add default autocomplete names
                    if table.name == 'autocomplete_values':
                        for value in self._default_autocomplete_values:
                            add_autocomplete_name(self.env, 
                                                     self._default_autocomplete_name, 
                                                     value)

                        #Remove shown_groups from config
                        self.config.set('autocomplete', 'shown_groups', None)
                        self.config.save()
                except Exception, ex:
                    self.log.exception('Failed to add tables. ')

def get_autocomplete_values(env, autocomplete_name):
    """Returns a list of values for the given autocomplete_name"""
    db = env.get_db_cnx()
    cursor = db.cursor()
    cursor.execute('SELECT value FROM autocomplete_values WHERE autocomplete_name = %s',
                   (autocomplete_name,))
    
    row = None
    values = []
    
    for row in cursor:
        values.append(row[0])

    return values

def add_autocomplete(env, autocomplete_name, description=None):
    """Adds an autocomplete section with description"""
    db = env.get_db_cnx()
    cursor = db.cursor()
    if not description:
        description = ""

    cursor.execute('''INSERT INTO autocomplete(name, description) VALUES 
                    (%s, %s)''',(autocomplete_name, description))
    
def add_autocomplete_name(env, autocomplete_name, value):
    """Adds an autocomplete value related to an autocomplete name"""
    db = env.get_db_cnx()
    cursor = db.cursor()
    
    relation_exists = check_if_section_name_exists(env, autocomplete_name, value)
    
    #Add data only if no relation exists
    if not relation_exists:
        cursor.execute('''INSERT INTO autocomplete_values(autocomplete_name, 
                        value) VALUES (%s, %s)''',(autocomplete_name, value))
        
def remove_autocomplete_name(env, autocomplete_name, value):
    """Remove an autocomplete value related to an autocomplete name"""
    db = env.get_db_cnx()
    cursor = db.cursor()
    
    relation_exists = check_if_section_name_exists(env, autocomplete_name, value)
    
    #Remove only if relation exists
    if relation_exists:
        cursor.execute('''DELETE FROM autocomplete_values WHERE 
                        autocomplete_name = %s AND value = %s''', 
                        (autocomplete_name, value))

def check_if_section_name_exists(env, autocomplete_name, value):
    """Checks if autocomplete_name name relation exists"""
    db = env.get_db_cnx()
    cursor = db.cursor()
    
    cursor.execute('''SELECT autocomplete_name FROM autocomplete_values WHERE
                    autocomplete_name = %s AND value = %s''', 
                    (autocomplete_name, value,))
    
    if cursor.fetchone() is None:
        return False
    return True
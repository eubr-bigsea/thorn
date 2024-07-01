import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, \
    DateTime, Text, Unicode
from sqlalchemy.orm import relationship
from sqlalchemy_i18n import make_translatable, translation_base, Translatable
make_translatable(options={'locales': ['pt', 'en'],
                           'auto_create_locales': False,
                           'fallback_locale': 'pt'})

db = SQLAlchemy()


# noinspection PyClassHasNoInit
class UserStatus:
    ENABLED = 'ENABLED'
    DELETED = 'DELETED'
    PENDING_APPROVAL = 'PENDING_APPROVAL'

    @staticmethod
    def values():
        return [n for n in list(UserStatus.__dict__.keys())
                if n[0] != '_' and n != 'values']


# noinspection PyClassHasNoInit
class EditorType:
    TEXT = 'TEXT'
    TEXTAREA = 'TEXTAREA'
    PASSWORD = 'PASSWORD'
    INTEGER = 'INTEGER'
    FLOAT = 'FLOAT'
    DATE = 'DATE'
    DATETIME = 'DATETIME'
    EMAIL = 'EMAIL'
    URL = 'URL'
    IMAGE = 'IMAGE'
    FILE = 'FILE'

    @staticmethod
    def values():
        return [n for n in list(EditorType.__dict__.keys())
                if n[0] != '_' and n != 'values']


# noinspection PyClassHasNoInit
class NotificationStatus:
    UNREAD = 'UNREAD'
    READ = 'READ'
    DELETED = 'DELETED'

    @staticmethod
    def values():
        return [n for n in list(NotificationStatus.__dict__.keys())
                if n[0] != '_' and n != 'values']


# noinspection PyClassHasNoInit
class NotificationType:
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

    @staticmethod
    def values():
        return [n for n in list(NotificationType.__dict__.keys())
                if n[0] != '_' and n != 'values']


# noinspection PyClassHasNoInit
class AssetType:
    DASHBOARD = 'DASHBOARD'
    DATA_SOURCE = 'DATA_SOURCE'
    SYSTEM = 'SYSTEM'
    JOB = 'JOB'
    DEPLOYMENT = 'DEPLOYMENT'
    API = 'API'
    APP = 'APP'
    VISUALIZATION = 'VISUALIZATION'
    USER = 'USER'
    PIPELINE = 'PIPELINE'
    PIPELINE_RUN = 'PIPELINE_RUN'
    EXPERIMENT = 'EXPERIMENT'
    EXPERIMENT_EXPLORER = 'EXPERIMENT_EXPLORER'
    EXPERIMENT_VISUALIZATION = 'EXPERIMENT_VISUALIZATION'
    EXPERIMENT_MODEL = 'EXPERIMENT_MODEL'
    EXPERIMENT_SQL = 'EXPERIMENT_SQL'
    WORKFLOW = 'WORKFLOW'

    @staticmethod
    def values():
        return [n for n in list(AssetType.__dict__.keys())
                if n[0] != '_' and n != 'values']


# noinspection PyClassHasNoInit
class AuthenticationType:
    AD = 'AD'
    INTERNAL = 'INTERNAL'
    LDAP = 'LDAP'
    OPENID = 'OPENID'

    @staticmethod
    def values():
        return [n for n in list(AuthenticationType.__dict__.keys())
                if n[0] != '_' and n != 'values']


# Association tables definition
    # noinspection PyUnresolvedReferences
role_permission = db.Table(
    'role_permission',
    Column('role_id', Integer,
           ForeignKey('role.id'),
           nullable=False, index=True),
    Column('permission_id', Integer,
           ForeignKey('permission.id'),
           nullable=False, index=True))
# noinspection PyUnresolvedReferences
user_role = db.Table(
    'user_role',
    Column('user_id', Integer,
           ForeignKey('user.id'),
           nullable=False, index=True),
    Column('role_id', Integer,
           ForeignKey('role.id'),
           nullable=False, index=True))


class Asset(db.Model):
    """ A protected asset in Lemonade """
    __tablename__ = 'asset'

    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    external_id = Column(String(100), nullable=False)
    type = Column(Enum(*list(AssetType.values()),
                       name='AssetTypeEnumType'), nullable=False)

    # Associations
    owner_id = Column(
        Integer,
        ForeignKey("user.id",
                   name="fk_asset_owner_id"),
        nullable=False,
        index=True)
    owner = relationship(
        "User",
        overlaps='assets',
        foreign_keys=[owner_id])

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class Configuration(db.Model, Translatable):
    """ Configuration in Lemonade """
    __tablename__ = 'configuration'
    __translatable__ = {'locales': ['pt', 'en']}

    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    value = Column(Text(4294000000), nullable=False)
    enabled = Column(Boolean,
                     default=True, nullable=False)
    internal = Column(Boolean,
                      default=True, nullable=False)
    editor = Column(Enum(*list(EditorType.values()),
                         name='EditorTypeEnumType'),
                    default='TEXT', nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class ConfigurationTranslation(translation_base(Configuration)):
    """ Translation table for Configuration """
    __tablename__ = 'configuration_translation'

    # Fields
    description = Column(Unicode(100))
    category = Column(Unicode(100))


class MailQueue(db.Model):
    """ Mail queue """
    __tablename__ = 'mail_queue'

    # Fields
    id = Column(Integer, primary_key=True)
    created = Column(DateTime,
                     default=datetime.datetime.utcnow, nullable=False,
                     onupdate=datetime.datetime.utcnow)
    status = Column(String(50), nullable=False)
    attempts = Column(Integer,
                      default=0, nullable=False)
    json_data = Column(Text(4294000000), nullable=False)

    def __str__(self):
        return self.created

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class Notification(db.Model):
    """ Notification """
    __tablename__ = 'notification'

    # Fields
    id = Column(Integer, primary_key=True)
    created = Column(DateTime,
                     default=datetime.datetime.utcnow, nullable=False,
                     onupdate=datetime.datetime.utcnow)
    text = Column(String(2000), nullable=False)
    link = Column(String(200))
    status = Column(Enum(*list(NotificationStatus.values()),
                         name='NotificationStatusEnumType'),
                    default="UNREAD", nullable=False)
    from_system = Column(Boolean,
                         default=True, nullable=False)
    type = Column(Enum(*list(NotificationType.values()),
                       name='NotificationTypeEnumType'),
                  default="INFO", nullable=False)

    # Associations
    user_id = Column(
        Integer,
        ForeignKey("user.id",
                   name="fk_notification_user_id"),
        nullable=False,
        index=True)
    user = relationship(
        "User",
        overlaps='user',
        foreign_keys=[user_id])

    def __str__(self):
        return self.created

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class Permission(db.Model, Translatable):
    """ Permission in Lemonade """
    __tablename__ = 'permission'
    __translatable__ = {'locales': ['pt', 'en']}

    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    applicable_to = Column(Enum(*list(AssetType.values()),
                                name='AssetTypeEnumType'))
    enabled = Column(Boolean,
                     default=True, nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class PermissionTranslation(translation_base(Permission)):
    """ Translation table for Permission """
    __tablename__ = 'permission_translation'

    # Fields
    description = Column(Unicode(100))


class Role(db.Model, Translatable):
    """ Roles in Lemonade """
    __tablename__ = 'role'
    __translatable__ = {'locales': ['pt', 'en']}

    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    all_user = Column(Boolean,
                      default=False, nullable=False)
    system = Column(Boolean,
                    default=False, nullable=False)
    enabled = Column(Boolean,
                     default=True, nullable=False)

    # Associations
    permissions = relationship(
        "Permission",
        overlaps="roles",
        secondary=role_permission,
        cascade="save-update")
    users = relationship(
        "User",
        overlaps="roles",
        secondary=user_role,
        cascade="save-update")

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class RoleTranslation(translation_base(Role)):
    """ Translation table for Role """
    __tablename__ = 'role_translation'

    # Fields
    label = Column(Unicode(100))
    description = Column(Unicode(100))


class User(db.Model):
    """ A user in Lemonade """
    __tablename__ = 'user'

    # Fields
    id = Column(Integer, primary_key=True)
    login = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    enabled = Column(Boolean,
                     default=True, nullable=False)
    status = Column(Enum(*list(UserStatus.values()),
                         name='UserStatusEnumType'),
                    default='ENABLED')
    authentication_type = Column(Enum(*list(AuthenticationType.values()),
                                      name='AuthenticationTypeEnumType'),
                                 default='INTERNAL')
    encrypted_password = Column(String(255), nullable=False)
    reset_password_token = Column(String(255))
    reset_password_sent_at = Column(DateTime,
                                    default=datetime.datetime.utcnow)
    remember_created_at = Column(DateTime)
    created_at = Column(DateTime,
                        default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime,
                        default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)
    first_name = Column(String(255))
    last_name = Column(String(255))
    locale = Column(String(20),
                    default='pt')
    confirmed_at = Column(DateTime)
    confirmation_sent_at = Column(DateTime)
    unconfirmed_email = Column(String(200))
    notes = Column(String(500))
    api_token = Column(String(200))

    # Associations
    roles = relationship(
        "Role",
        overlaps="users",
        secondary=user_role,
        cascade="delete",
        secondaryjoin=(
            "and_("
            "Role.id==user_role.c.role_id,"
            "Role.enabled==True)"))
    workspace_id = Column(
        Integer,
        ForeignKey("workspace.id",
                   name="fk_user_workspace_id",
                   use_alter=True),
        index=True)
    workspace = relationship(
        "Workspace",
        overlaps='users',
        foreign_keys=[workspace_id])

    def __str__(self):
        return self.login

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class UserPermissionForAsset(db.Model):
    """ User permission for an asset """
    __tablename__ = 'user_permission_for_asset'

    # Fields
    id = Column(Integer, primary_key=True)

    def __str__(self):
        return 'UserPermissionForAsset'

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class UserPreference(db.Model):
    """ User preference """
    __tablename__ = 'user_preference'

    # Fields
    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False)
    value = Column(Text(4294000000), nullable=False)

    # Associations
    user_id = Column(
        Integer,
        ForeignKey("user.id",
                   name="fk_user_preference_user_id"),
        nullable=False,
        index=True)
    user = relationship(
        "User",
        overlaps='preferences',
        foreign_keys=[user_id])

    def __str__(self):
        return self.key

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


class Workspace(db.Model):
    """ A user workspace in Lemonade """
    __tablename__ = 'workspace'

    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)

    # Associations
    owner_id = Column(
        Integer,
        ForeignKey("user.id",
                   name="fk_workspace_owner_id"),
        nullable=False,
        index=True)
    owner = relationship(
        "User",
        overlaps='workspaces',
        foreign_keys=[owner_id])

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Instance {}: {}>'.format(self.__class__, self.id)


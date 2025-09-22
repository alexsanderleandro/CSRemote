"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Criar tabela usuarios
    op.create_table('usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('senha_hash', sa.String(length=255), nullable=False),
        sa.Column('tipo_usuario', sa.String(length=20), nullable=False),
        sa.Column('administrador', sa.Boolean(), nullable=True),
        sa.Column('empresa', sa.String(length=200), nullable=True),
        sa.Column('cnpj', sa.String(length=18), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)
    op.create_index(op.f('ix_usuarios_id'), 'usuarios', ['id'], unique=False)
    
    # Criar tabela sessoes_remotas
    op.create_table('sessoes_remotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analista_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('codigo_acesso', sa.String(length=10), nullable=False),
        sa.Column('maquina_cliente', sa.String(length=255), nullable=True),
        sa.Column('inicio', sa.DateTime(), nullable=True),
        sa.Column('termino', sa.DateTime(), nullable=True),
        sa.Column('trafego_bytes', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['analista_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['cliente_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessoes_remotas_codigo_acesso'), 'sessoes_remotas', ['codigo_acesso'], unique=False)
    op.create_index(op.f('ix_sessoes_remotas_id'), 'sessoes_remotas', ['id'], unique=False)
    
    # Criar tabela mensagens_chat
    op.create_table('mensagens_chat',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sessao_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sessao_id'], ['sessoes_remotas.id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mensagens_chat_id'), 'mensagens_chat', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_mensagens_chat_id'), table_name='mensagens_chat')
    op.drop_table('mensagens_chat')
    op.drop_index(op.f('ix_sessoes_remotas_id'), table_name='sessoes_remotas')
    op.drop_index(op.f('ix_sessoes_remotas_codigo_acesso'), table_name='sessoes_remotas')
    op.drop_table('sessoes_remotas')
    op.drop_index(op.f('ix_usuarios_id'), table_name='usuarios')
    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')

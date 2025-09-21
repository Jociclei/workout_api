from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import List, Optional
from fastapi_pagination import Page, add_pagination, paginate
from fastapi_pagination.params import PaginationParams

# Configuração do banco de dados SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./atletas.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models do SQLAlchemy
class CentroTreinamentoModel(Base):
    __tablename__ = "centros_treinamento"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    
    atletas = relationship("AtletaModel", back_populates="centro_treinamento")

class CategoriaModel(Base):
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    
    atletas = relationship("AtletaModel", back_populates="categoria")

class AtletaModel(Base):
    __tablename__ = "atletas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cpf = Column(String, unique=True, nullable=False)
    centro_treinamento_id = Column(Integer, ForeignKey("centros_treinamento.id"))
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    
    centro_treinamento = relationship("CentroTreinamentoModel", back_populates="atletas")
    categoria = relationship("CategoriaModel", back_populates="atletas")

# Criar as tabelas
Base.metadata.create_all(bind=engine)

# Pydantic Models
class CentroTreinamentoResponse(BaseModel):
    nome: str
    
    class Config:
        orm_mode = True

class CategoriaResponse(BaseModel):
    nome: str
    
    class Config:
        orm_mode = True

class AtletaResponse(BaseModel):
    nome: str
    centro_treinamento: CentroTreinamentoResponse
    categoria: CategoriaResponse
    
    class Config:
        orm_mode = True

class AtletaCreate(BaseModel):
    nome: str
    cpf: str
    centro_treinamento_id: int
    categoria_id: int

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inicializar a aplicação FastAPI
app = FastAPI(title="API de Atletas")

# Adicionar paginação
add_pagination(app)

# Endpoints
@app.get("/atletas", response_model=Page[AtletaResponse])
def get_all_atletas(
    db: Session = Depends(get_db),
    nome: Optional[str] = Query(None, description="Filtrar por nome do atleta"),
    cpf: Optional[str] = Query(None, description="Filtrar por CPF do atleta"),
    params: PaginationParams = Depends()
):
    query = db.query(AtletaModel)
    
    if nome:
        query = query.filter(AtletaModel.nome.ilike(f"%{nome}%"))
    
    if cpf:
        query = query.filter(AtletaModel.cpf == cpf)
    
    return paginate(query.all(), params)

@app.post("/atletas", response_model=AtletaResponse)
def create_atleta(atleta: AtletaCreate, db: Session = Depends(get_db)):
    try:
        db_atleta = AtletaModel(**atleta.dict())
        db.add(db_atleta)
        db.commit()
        db.refresh(db_atleta)
        return db_atleta
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=303, 
            detail=f"Já existe um atleta cadastrado com o cpf: {atleta.cpf}"
        )

# Popular o banco com alguns dados iniciais
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    
    # Verificar se já existem dados
    if not db.query(CentroTreinamentoModel).first():
        # Criar centros de treinamento
        centros = [
            CentroTreinamentoModel(nome="CT Rio de Janeiro"),
            CentroTreinamentoModel(nome="CT São Paulo"),
            CentroTreinamentoModel(nome="CT Minas Gerais")
        ]
        db.add_all(centros)
        
        # Criar categorias
        categorias = [
            CategoriaModel(nome="Junior"),
            CategoriaModel(nome="Pleno"),
            CategoriaModel(nome="Sênior")
        ]
        db.add_all(categorias)
        
        db.commit()
    
    db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from src.interfaces.tasks import TaskCreate, TaskUpdate
from src.models.tasks import Task as TaskModel
from src.models.users import User as UserModel
from src.utils.db import get_db
from src.utils.helper import is_autheticated


tasks_router = APIRouter(
    prefix="/tasks",
    dependencies=[Depends(is_autheticated)],
)

# route level auth middleware:

@tasks_router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    db=Depends(get_db),
    user: UserModel = Depends(is_autheticated),
):

    try:
        task = TaskModel(**body.model_dump(), user_id=user.id)
        db.add(task)
        db.commit()
        db.refresh(task)
        
    except SQLAlchemyError:
        db.rollback()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )

    return {
        "message": "Task created successfully",
        "data": task
    }
    

@tasks_router.get("/", status_code=status.HTTP_200_OK)
async def get_tasks(
    db=Depends(get_db),
    user: UserModel = Depends(is_autheticated),
):
    
    tasks = db.query(TaskModel).filter(TaskModel.user_id == user.id).limit(50).all()
    return {
        "message": "Tasks fetched successfully",
        "data": tasks
    }


@tasks_router.get("/{task_id}", status_code=status.HTTP_200_OK)
async def get_task(
    task_id: int,
    db=Depends(get_db),
    user: UserModel = Depends(is_autheticated),
):
    
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.user_id == user.id,
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "message": "Task fetched successfully",
        "data": task
    }


@tasks_router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db = Depends(get_db),
    user: UserModel = Depends(is_autheticated),
):
    
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.user_id == user.id,
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        db.delete(task)
        db.commit()
    except SQLAlchemyError:
        
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )
    
    return {
        "message": "Task deleted successfully"
    }


@tasks_router.put("/{task_id}", status_code=status.HTTP_200_OK)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    db = Depends(get_db),
    user: UserModel = Depends(is_autheticated),
):
    
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.user_id == user.id,
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        if body.title is not None:
            task.title = body.title
        if body.description is not None:
            task.description = body.description
        if body.is_completed is not None:
            task.is_completed = body.is_completed
        
        db.commit()
        db.refresh(task)
    except SQLAlchemyError:
        
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )
    
    return {
        "message": "Task updated successfully",
        "data": task
    }

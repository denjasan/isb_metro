class Settings:
    DATABASE_DSN: str = "postgresql://postgres:mYy5RexGsZ@localhost/isb_metro"
    SECRET_KEY: str = "$2b$12$ejEmyvRBu.UnwWtV7VWXg../GHlwJvBJHwZTgK2Vx5lTbItJWAEVy"

    # Определяем константы ролей
    ROLE_PS = "ПС"  # Производственная служба
    ROLE_TS = "ТС"  # Техническая служба
    ROLE_SS = "СС"  # Сметная служба
    ROLE_SM = "СМ"  # Служба механизации
    ROLE_SZP = "СЗиП"  # Служба закупок и поставок
    ROLE_CUST = "Заказчик"
    ROLE_MGR = "Руководитель контракта"
    ALL = [ROLE_SS, ROLE_TS, ROLE_PS, ROLE_CUST, ROLE_MGR, ROLE_SM, ROLE_SZP]

    # 1. Сметная документация
    ESTIMATE_VIEW = ALL
    ESTIMATE_EDIT = [ROLE_SS, ROLE_MGR]

    # 2. Спецификация материалов и оборудования (ведомость)
    MATERIALS_VIEW = ALL
    MATERIALS_EDIT = [ROLE_SZP, ROLE_MGR]

    # 3. Справочник материалов и оборудования
    MATERIALS_REF_VIEW = ALL
    MATERIALS_REF_EDIT = [ROLE_SZP, ROLE_MGR]

    # 4. Ведомость основных механизмов
    MECHANISMS_VIEW = ALL
    MECHANISMS_EDIT = [ROLE_SM, ROLE_MGR]

    # 5. Справочник механизмов
    MECHANISMS_REF_VIEW = ALL
    MECHANISMS_REF_EDIT = [ROLE_SM, ROLE_MGR]

    # 6. График строительства (work_volumes)
    WORK_VOLUMES_VIEW = ALL
    WORK_VOLUMES_EDIT = [ROLE_TS, ROLE_MGR, ROLE_PS, ROLE_CUST]

    # 7. Строители / специалисты (PS схема строителей)
    BUILDERS_SPECIALISTS_VIEW = ALL
    BUILDERS_SPECIALISTS_EDIT = [ROLE_PS, ROLE_MGR]

    # 8. ИТР (схема по инженерно-техническим работникам)
    ITR_VIEW = ALL
    ITR_EDIT = [ROLE_PS, ROLE_MGR]

    # 9. АУП (схема административно-управленческого персонала)
    AUP_VIEW = ALL
    AUP_EDIT = [ROLE_MGR]

    class Config:
        env_file = ".env"

settings = Settings()

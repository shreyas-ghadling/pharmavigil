-- =====================================================================
-- PHARMAVIGIL: STORED PROCEDURES (MySQL 8.0+)
-- Atomic Emergency Batch Recall with Transactional Audit Logging
-- =====================================================================

USE pharmavigil_db;

DROP PROCEDURE IF EXISTS sp_recall_batch_v2;

DELIMITER //

CREATE PROCEDURE sp_recall_batch_v2(
    IN p_batch_number VARCHAR(50),
    IN p_reason VARCHAR(255),
    IN p_recalled_by VARCHAR(100),
    OUT p_affected_hospitals INT,
    OUT p_total_units_recalled INT
)
proc_label: BEGIN
    DECLARE v_batch_exists INT DEFAULT 0;
    DECLARE v_current_status VARCHAR(25) DEFAULT NULL;
    
    -- Transaction exception handler with automated rollback
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- The batch lock is shared with receipt and dispatch transactions.
    START TRANSACTION;
    SELECT recall_status INTO v_current_status
    FROM batches WHERE batch_number = p_batch_number FOR UPDATE;
    SET v_batch_exists = (v_current_status IS NOT NULL);

    IF v_batch_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Batch recall failed: Specified batch number does not exist in the database.';
    END IF;

    -- 2. Verify batch is not already recalled (prevent duplicate recalls and audit pollution)
    IF v_current_status = 'RECALLED' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Batch recall refused: Specified batch is already RECALLED.';
    END IF;


        -- Step A: Transition batch status to RECALLED
        UPDATE batches
        SET recall_status = 'RECALLED'
        WHERE batch_number = p_batch_number;

        -- Step B: Calculate affected hospitals and total units delivered
        SELECT 
            COUNT(DISTINCT hospital_id),
            COALESCE(SUM(quantity_delivered), 0)
        INTO 
            p_affected_hospitals,
            p_total_units_recalled
        FROM batch_distribution
        WHERE batch_number = p_batch_number;

        -- Step C: Insert transactional audit log
        INSERT INTO recall_audit (
            batch_number,
            reason,
            recalled_by,
            affected_hospitals,
            total_units_recalled,
            recalled_at
        ) VALUES (
            p_batch_number,
            COALESCE(p_reason, 'Adverse Drug Reaction Threshold Breached'),
            COALESCE(p_recalled_by, 'SAFETY_OFFICER_ADMIN'),
            p_affected_hospitals,
            p_total_units_recalled,
            NOW()
        );

    COMMIT;
END //

DELIMITER ;

SELECT
    SCHEMA_NAME(t.schema_id) AS SchemaName,
    t.NAME AS TableName,
    COUNT(DISTINCT c.column_id) AS Cols,
    CONVERT(INT, p.[Rows]) AS Recs
FROM sys.tables t
         INNER JOIN sys.indexes i ON t.OBJECT_ID = i.object_id
         INNER JOIN sys.partitions p ON i.object_id = p.OBJECT_ID AND i.index_id = p.index_id
         INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
         JOIN sys.columns c ON t.object_id = c.object_id

WHERE
    t.NAME NOT LIKE 'dt%' AND
    i.OBJECT_ID > 255 AND
    i.index_id <= 1
GROUP BY
    SCHEMA_NAME(t.schema_id), t.NAME, i.object_id, i.index_id, i.name, p.[Rows]
ORDER BY
    object_name(i.object_id);
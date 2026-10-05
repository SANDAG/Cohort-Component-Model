-- Create 'outputs' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'outputs')
BEGIN
    EXEC('CREATE [SCHEMA] [outputs]')
END
GO

-- Create 'metadata' schema if it does not exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'metadata')
BEGIN
    EXEC('CREATE [SCHEMA] [metadata]')
END
GO


-- Create Table 'metadata.run'
CREATE TABLE [metadata].[run]
(
    [run_id] INT NOT NULL,
	[launch] INT NOT NULL,
	[horizon] INT NOT NULL,
    [user] NVARCHAR(100) NOT NULL, 
    [start_date] DATETIME NOT NULL,
    [end_date] DATETIME NULL,
    [version] NVARCHAR(50) NOT NULL,
    [comments] NVARCHAR(MAX) NULL,
    [complete] BIT NOT NULL,
    CONSTRAINT [pk_metadata_run] PRIMARY KEY ([run_id])
) WITH (DATA_COMPRESSION = PAGE);
GO


-- Create Table 'outputs.components'
CREATE TABLE [outputs].[components]
(
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [age] INT NOT NULL,
    [sex] NVARCHAR(5) NOT NULL,
    [ethnicity] NVARCHAR(150) NOT NULL,
    [births] INT NOT NULL,
    [deaths] INT NOT NULL,
    [ins] INT NOT NULL,
    [outs] INT NOT NULL,
    INDEX [ccsi_outputs_components] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_components] UNIQUE ([run_id], [year], [age], [sex], [ethnicity]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_components_run] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
)
GO


-- Create Table 'outputs.population'
CREATE TABLE [outputs].[population]
(
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [age] INT NOT NULL,
    [sex] NVARCHAR(5) NOT NULL,
    [ethnicity] NVARCHAR(150) NOT NULL,
    [pop] INT NOT NULL,
    [gq_mil] INT NOT NULL,
    [gq_prison] INT NOT NULL,
    [gq_college] INT NOT NULL,
    [gq_other] INT NOT NULL,
    [hh] INT NOT NULL,
    [hh_size1] INT NOT NULL,
    [hh_size2] INT NOT NULL,
    [hh_size3] INT NOT NULL,
    [hh_workers0] INT NOT NULL,
    [hh_workers1] INT NOT NULL,
    [hh_workers2] INT NOT NULL,
    [hh_workers3] INT NOT NULL,
    [hh_head_lf] INT NOT NULL,
    [hh_children] INT NOT NULL,
    [hh_seniors] INT NOT NULL,
    INDEX [ccsi_outputs_population] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_population] UNIQUE ([run_id], [year], [age], [sex], [ethnicity]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_population_run] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
)
GO


-- Create Table 'outputs.rates'
CREATE TABLE [outputs].[rates]
(
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [age] INT NOT NULL,
    [sex] NVARCHAR(5) NOT NULL,
    [ethnicity] NVARCHAR(150) NOT NULL,
    [rate_birth] FLOAT NOT NULL,
    [rate_death] FLOAT NOT NULL,
    [rate_in] FLOAT NOT NULL,
    [rate_out] FLOAT NOT NULL,
    [rate_gq_college] FLOAT NOT NULL,
    [rate_gq_other] FLOAT NOT NULL,
    [rate_hh] FLOAT NOT NULL,
    [rate_hh_size1] FLOAT NOT NULL,
    [rate_hh_size2] FLOAT NOT NULL,
    [rate_hh_size3] FLOAT NOT NULL,
    [rate_hh_workers0] FLOAT NOT NULL,
    [rate_hh_workers1] FLOAT NOT NULL,
    [rate_hh_workers2] FLOAT NOT NULL,
    [rate_hh_workers3] FLOAT NOT NULL,
    [rate_hh_head_lf] FLOAT NOT NULL,
	[rate_hh_children] FLOAT NOT NULL,
    [rate_hh_seniors] FLOAT NOT NULL,
    INDEX [ccsi_outputs_rates] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_rates] UNIQUE ([run_id], [year], [age], [sex], [ethnicity]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_rates_run] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
)
GO
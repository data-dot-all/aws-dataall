import React from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { styled } from '@mui/styles';
import { Card } from '@mui/material';

const StyledDataGrid = styled(DataGrid)(({ theme }) => ({
  '& .MuiDataGrid-columnsContainer': {
    backgroundColor:
      theme.palette.mode === 'dark'
        ? 'rgba(29,29,29,0.33)'
        : 'rgba(255,255,255,0.38)'
  }
}));
const buildHeader = (fields) =>
  fields.map((field) => ({
    field: JSON.parse(field).name,
    headerName: JSON.parse(field).name,
    editable: false
  }));
const buildRows = (rows, fields) => {
  const header = fields.map((field) => JSON.parse(field).name);
  const newRows = rows.map((row) => JSON.parse(row));
  const builtRows = newRows.map((row) =>
    header.map((h, index) => ({ [h]: row[index] }))
  );
  const objects = [];
  builtRows.forEach((row) => {
    const obj = {};
    row.forEach((r) => {
      Object.entries(r).forEach(([key, value]) => {
        obj[key] = value;
      });
      obj.id = Math.random();
    });
    objects.push(obj);
  });
  return objects;
};
const SampleDataTableComponent = ({ data }) => {
  return (
    <Card sx={{ height: 400, width: 900 }}>
      <StyledDataGrid
        disableColumnResize={false}
        disableColumnReorder={false}
        rows={buildRows(data.rows, data.fields)}
        columns={buildHeader(data.fields)}
      />
    </Card>
  );
};

export default SampleDataTableComponent;

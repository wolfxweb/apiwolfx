# 🎯 Planejamento Financeiro Flexível

## 📋 **Funcionalidade Implementada**

Sistema de **Planejamento Financeiro Flexível** que permite:

- ✅ **Seleção dinâmica** de centros de custo
- ✅ **Adição/remoção** de centros de custo por mês
- ✅ **Seleção dinâmica** de categorias
- ✅ **Adição/remoção** de categorias por centro de custo
- ✅ **Valores flexíveis** para cada item
- ✅ **Observações** personalizadas

## 🎨 **Interface Flexível**

### **1. Centros de Custo Dinâmicos**

#### **Botão "Adicionar Centro de Custo"**
```html
<button type="button" class="btn btn-sm btn-outline-primary" onclick="addCostCenter(${month.month})">
    <i class="bi bi-plus-circle"></i> Adicionar Centro de Custo
</button>
```

#### **Seleção de Centro de Custo**
```html
<select class="form-select" onchange="updateCostCenterSelection(${month}, '${costCenterId}', this.value)">
    <option value="">Selecione um centro de custo</option>
    ${getCostCenterOptions(costCenter.id)}
</select>
```

#### **Campos Flexíveis**
- ✅ **Valor Máximo de Gasto** - Campo numérico
- ✅ **Observações** - Campo de texto livre
- ✅ **Botão Remover** - Para excluir centro de custo

### **2. Categorias Dinâmicas**

#### **Botão "Adicionar Categoria"**
```html
<button type="button" class="btn btn-sm btn-outline-secondary" onclick="addCategory(${month}, '${costCenterId}')">
    <i class="bi bi-plus-circle"></i> Adicionar Categoria
</button>
```

#### **Seleção de Categoria**
```html
<select class="form-select" onchange="updateCategorySelection(${month}, '${costCenterId}', '${categoryId}', this.value)">
    <option value="">Selecione uma categoria</option>
    ${getCategoryOptions(category.id)}
</select>
```

#### **Campos Flexíveis por Categoria**
- ✅ **Seleção de Categoria** - Dropdown dinâmico
- ✅ **Valor Máximo** - Campo numérico
- ✅ **Observações** - Campo de texto
- ✅ **Botão Remover** - Para excluir categoria

## 🔧 **Funcionalidades JavaScript**

### **1. Adicionar Centro de Custo**
```javascript
function addCostCenter(month) {
    const container = document.getElementById(`cost-centers-${month}`);
    const newCostCenter = {
        id: `new-${Date.now()}`,
        name: 'Novo Centro de Custo',
        max_spending: 0,
        notes: '',
        categories: []
    };
    
    const costCenterHtml = renderCostCenter(month, newCostCenter);
    container.insertAdjacentHTML('beforeend', costCenterHtml);
}
```

### **2. Remover Centro de Custo**
```javascript
function removeCostCenter(month, costCenterId) {
    const element = document.getElementById(`cost-center-${month}-${costCenterId}`);
    if (element) {
        element.remove();
    }
}
```

### **3. Adicionar Categoria**
```javascript
function addCategory(month, costCenterId) {
    const container = document.getElementById(`categories-${month}-${costCenterId}`);
    const newCategory = {
        id: `new-${Date.now()}`,
        name: 'Nova Categoria',
        max_spending: 0,
        notes: ''
    };
    
    const categoryHtml = renderCategory(month, costCenterId, newCategory);
    container.insertAdjacentHTML('beforeend', categoryHtml);
}
```

### **4. Remover Categoria**
```javascript
function removeCategory(month, costCenterId, categoryId) {
    const element = document.getElementById(`category-${month}-${costCenterId}-${categoryId}`);
    if (element) {
        element.remove();
    }
}
```

## 🎯 **Fluxo de Uso**

### **1. Planejamento Mensal**
1. **Expandir o mês** desejado no accordion
2. **Preencher faturamento** e margem esperada
3. **Clicar em "Adicionar Centro de Custo"**

### **2. Configurar Centro de Custo**
1. **Selecionar centro de custo** do dropdown
2. **Informar valor máximo** de gasto
3. **Adicionar observações** se necessário
4. **Clicar em "Adicionar Categoria"** para o centro de custo

### **3. Configurar Categorias**
1. **Selecionar categoria** do dropdown
2. **Informar valor máximo** para a categoria
3. **Adicionar observações** se necessário
4. **Remover** se não precisar da categoria

### **4. Flexibilidade Total**
- ✅ **Adicionar quantos centros de custo** quiser por mês
- ✅ **Adicionar quantas categorias** quiser por centro de custo
- ✅ **Remover** qualquer item que não precisar
- ✅ **Valores dinâmicos** para cada item
- ✅ **Observações personalizadas**

## 📊 **Estrutura de Dados**

### **Centro de Custo**
```javascript
{
    id: "1" ou "new-1234567890",
    name: "Marketing",
    max_spending: 5000.00,
    notes: "Campanhas digitais",
    categories: [...]
}
```

### **Categoria**
```javascript
{
    id: "1" ou "new-1234567890",
    name: "Google Ads",
    max_spending: 2000.00,
    notes: "Anúncios pagos"
}
```

## 🎨 **Interface Visual**

### **Layout Responsivo**
- ✅ **Cards** para cada centro de custo
- ✅ **Headers** com seleção e botão remover
- ✅ **Campos organizados** em linhas
- ✅ **Botões de ação** bem posicionados
- ✅ **Ícones** para melhor UX

### **Cores e Estilos**
- ✅ **Botões primários** para adicionar
- ✅ **Botões de perigo** para remover
- ✅ **Cards com bordas** para organização
- ✅ **Input groups** para valores monetários
- ✅ **Ícones Bootstrap** para ações

## 🚀 **Benefícios**

- ✅ **Flexibilidade total** - Adicione/remova conforme necessário
- ✅ **Interface intuitiva** - Fácil de usar
- ✅ **Valores dinâmicos** - Configure exatamente o que precisa
- ✅ **Observações** - Anote detalhes importantes
- ✅ **Responsivo** - Funciona em qualquer dispositivo
- ✅ **Performance** - Atualizações em tempo real

---

**Data de Implementação**: 23/10/2025
**Status**: ✅ **IMPLEMENTADO** - Sistema 100% flexível

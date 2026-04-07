/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";

class FormLayoutBuilder extends Component {
    static template = "theme_ui_custom.FormLayoutBuilder";
    static props = ["modelId", "layoutConfig", "onUpdate"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        this.state = useState({
            availableFields: [],
            tabs: this.props.layoutConfig?.tabs || [],
            fields: this.props.layoutConfig?.fields || [],
            draggedField: null,
            draggedFrom: null,
        });
        
        this.containerRef = useRef("container");
        
        this.loadFields();
    }

    async loadFields() {
        if (!this.props.modelId) {
            return;
        }
        
        try {
            const fields = await this.orm.call("ui.form.layout", "get_available_fields", [this.props.modelId]);
            this.state.availableFields = fields || [];
        } catch (error) {
            console.error("Error loading fields:", error);
            this.notification.add("Error loading available fields", { type: "danger" });
        }
    }

    onDragStart(event, field, from) {
        this.state.draggedField = field;
        this.state.draggedFrom = from;
        event.dataTransfer.setData("text/plain", JSON.stringify({ field, from }));
        event.dataTransfer.effectAllowed = "move";
    }

    onDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
    }

    onDrop(event, target, targetIndex) {
        event.preventDefault();
        
        if (!this.state.draggedField) {
            return;
        }

        const field = this.state.draggedField;
        const from = this.state.draggedFrom;

        if (from === "available") {
            if (target === "fields") {
                const newFields = [...this.state.fields];
                newFields.splice(targetIndex !== undefined ? targetIndex : newFields.length, 0, field.name);
                this.state.fields = newFields;
            } else if (target === "tab" && targetIndex !== undefined) {
                const tabIndex = targetIndex;
                const newTabs = [...this.state.tabs];
                if (!newTabs[tabIndex].fields) {
                    newTabs[tabIndex].fields = [];
                }
                newTabs[tabIndex].fields.push(field.name);
                this.state.tabs = newTabs;
            }
        } else if (from === "fields") {
            if (target === "fields") {
                const newFields = this.state.fields.filter(f => f !== field.name);
                newFields.splice(targetIndex !== undefined ? targetIndex : newFields.length, 0, field.name);
                this.state.fields = newFields;
            } else if (target === "tab" && targetIndex !== undefined) {
                const newFields = this.state.fields.filter(f => f !== field.name);
                this.state.fields = newFields;
                
                const newTabs = [...this.state.tabs];
                if (!newTabs[targetIndex].fields) {
                    newTabs[targetIndex].fields = [];
                }
                newTabs[targetIndex].fields.push(field.name);
                this.state.tabs = newTabs;
            }
        } else if (from === "tab") {
            const tabIndex = from.tabIndex;
            const newTabs = [...this.state.tabs];
            newTabs[tabIndex].fields = (newTabs[tabIndex].fields || []).filter(f => f !== field.name);
            this.state.tabs = newTabs;
            
            if (target === "fields") {
                const newFields = [...this.state.fields];
                newFields.splice(targetIndex !== undefined ? targetIndex : newFields.length, 0, field.name);
                this.state.fields = newFields;
            } else if (target === "tab" && targetIndex !== undefined) {
                const targetTabs = [...this.state.tabs];
                if (!targetTabs[targetIndex].fields) {
                    targetTabs[targetIndex].fields = [];
                }
                targetTabs[targetIndex].fields.push(field.name);
                this.state.tabs = targetTabs;
            }
        }

        this.state.draggedField = null;
        this.state.draggedFrom = null;
        this.saveConfig();
    }

    onDropOnContainer(event) {
        event.preventDefault();
        
        if (!this.state.draggedField) {
            return;
        }

        const field = this.state.draggedField;
        const from = this.state.draggedFrom;

        if (from === "tab") {
            const tabIndex = from.tabIndex;
            const newTabs = [...this.state.tabs];
            newTabs[tabIndex].fields = (newTabs[tabIndex].fields || []).filter(f => f !== field.name);
            this.state.tabs = newTabs;
            
            const newFields = [...this.state.fields];
            newFields.push(field.name);
            this.state.fields = newFields;
        }

        this.state.draggedField = null;
        this.state.draggedFrom = null;
        this.saveConfig();
    }

    addTab() {
        const newTabs = [...this.state.tabs, { name: "New Tab", fields: [] }];
        this.state.tabs = newTabs;
        this.saveConfig();
    }

    removeTab(index) {
        const tab = this.state.tabs[index];
        const newFields = [...this.state.fields, ...(tab.fields || [])];
        const newTabs = this.state.tabs.filter((_, i) => i !== index);
        this.state.fields = newFields;
        this.state.tabs = newTabs;
        this.saveConfig();
    }

    updateTabName(index, name) {
        const newTabs = [...this.state.tabs];
        newTabs[index].name = name;
        this.state.tabs = newTabs;
        this.saveConfig();
    }

    removeFieldFromTab(tabIndex, fieldIndex) {
        const newTabs = [...this.state.tabs];
        const field = newTabs[tabIndex].fields[fieldIndex];
        newTabs[tabIndex].fields.splice(fieldIndex, 1);
        this.state.tabs = newTabs;
        
        const newFields = [...this.state.fields, field];
        this.state.fields = newFields;
        this.saveConfig();
    }

    removeField(index) {
        const newFields = this.state.fields.filter((_, i) => i !== index);
        this.state.fields = newFields;
        this.saveConfig();
    }

    saveConfig() {
        const config = {
            tabs: this.state.tabs,
            fields: this.state.fields,
        };
        
        if (this.props.onUpdate) {
            this.props.onUpdate(config);
        }
    }

    getFieldValue(name) {
        return this.state.availableFields.find(f => f.name === name);
    }
}

FormLayoutBuilder.props = {
    modelId: { type: Number, optional: true },
    layoutConfig: { type: Object, optional: true },
    onUpdate: { type: Function, optional: true },
};

registry.category("fields").add("form_layout_builder", {
    component: FormLayoutBuilder,
    supportedTypes: ["json"],
    extractProps: ({ attrs }) => ({
        modelId: attrs.options?.modelId,
        layoutConfig: attrs.options?.layoutConfig,
        onUpdate: attrs.options?.onUpdate,
    }),
});

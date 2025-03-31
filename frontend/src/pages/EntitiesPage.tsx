import { useEffect, useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableCaption,
  TableHead,
  TableHeader,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { Trash, Pencil } from "lucide-react";

interface EntityRecord {
  id: string;
  data: any;
}

interface EntitiesPageProps {
  token: string;
}

export function EntitiesPage({ token }: EntitiesPageProps) {
  const [types, setTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState("");
  const [entities, setEntities] = useState<EntityRecord[]>([]);
  const [newEntityData, setNewEntityData] = useState("{}");

  // New states for creating a new type (schema)
  const [newTypeName, setNewTypeName] = useState("");
  const [newSchemaData, setNewSchemaData] = useState(
    '{"type": "object", "properties": {}}',
  );

  // New states for inline editing
  const [editingEntity, setEditingEntity] = useState<EntityRecord | null>(null);
  const [editingJson, setEditingJson] = useState("");

  // Fetch available schema types
  useEffect(() => {
    fetch("/api/schemas", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.schemas && Array.isArray(data.schemas)) {
          const typeList = data.schemas.map((s: any) => s.type);
          setTypes(typeList);
          if (typeList.length > 0) {
            setSelectedType(typeList[0]);
          } else {
            setSelectedType("new");
          }
        }
      })
      .catch((err) => console.error("Error fetching schemas", err));
  }, [token]);

  // Fetch entities of selectedType when an existing type is chosen
  useEffect(() => {
    if (!selectedType || selectedType === "new") return;
    fetch(`/api/schemas/${encodeURIComponent(selectedType)}/entities`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.entities && Array.isArray(data.entities)) {
          setEntities(data.entities);
        } else {
          setEntities([]);
        }
      })
      .catch((err) => console.error("Error fetching entities", err));
  }, [selectedType, token]);

  const handleCreate = async () => {
    try {
      const parsedData = JSON.parse(newEntityData);
      const res = await fetch(
        `/api/schemas/${encodeURIComponent(selectedType)}/entities`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            type: selectedType,
            data: parsedData,
          }),
        },
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert(`Create failed: ${errData.description || res.statusText}`);
        return;
      }
      const result = await res.json();
      alert(`Entity created with ID: ${result.id}`);
      setNewEntityData("{}");
      // Refetch entities
      fetch(`/api/schemas/${encodeURIComponent(selectedType)}/entities`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((d) => setEntities(d.entities || []));
    } catch (e: any) {
      alert(`Invalid JSON or other error: ${e.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this entity?")) return;
    const res = await fetch(
      `/api/schemas/${encodeURIComponent(selectedType)}/entities/${id}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      alert(`Delete failed: ${errData.description || res.statusText}`);
      return;
    }
    // Update local list
    setEntities(entities.filter((e) => e.id !== id));
  };

  const handleCreateSchema = async () => {
    try {
      const parsedSchema = JSON.parse(newSchemaData);
      const res = await fetch("/api/schemas", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: newTypeName,
          schema: parsedSchema,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert(
          `Schema creation failed: ${errData.description || res.statusText}`,
        );
        return;
      }
      await res.json();
      alert(`Schema created for type: ${newTypeName}`);
      // Update types list and select the new type
      setTypes([...types, newTypeName]);
      setSelectedType(newTypeName);
      setNewTypeName("");
      setNewSchemaData('{"type": "object", "properties": {}}');
    } catch (e: any) {
      alert(`Invalid JSON or other error: ${e.message}`);
    }
  };

  const handleEdit = (entity: EntityRecord) => {
    setEditingEntity(entity);
    setEditingJson(JSON.stringify(entity.data, null, 2));
  };

  const handleUpdate = async () => {
    if (!editingEntity) return;
    try {
      const parsedData = JSON.parse(editingJson);
      const res = await fetch(
        `/api/schemas/${encodeURIComponent(selectedType)}/entities/${
          editingEntity.id
        }`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            data: parsedData,
          }),
        },
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert(`Update failed: ${errData.description || res.statusText}`);
        return;
      }
      // Refetch entities
      fetch(`/api/schemas/${encodeURIComponent(selectedType)}/entities`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((d) => setEntities(d.entities || []));
      alert(`Entity updated with ID: ${editingEntity.id}`);
      setEditingEntity(null);
      setEditingJson("");
    } catch (e: any) {
      alert(`Invalid JSON or other error: ${e.message}`);
    }
  };

  // Compute union of keys from all entities
  const dataKeys = useMemo(() => {
    const keysSet = new Set<string>();
    entities.forEach((entity) => {
      if (entity.data && typeof entity.data === "object") {
        Object.keys(entity.data).forEach((key) => keysSet.add(key));
      }
    });
    return Array.from(keysSet);
  }, [entities]);

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Entities</h1>

      <div className="mb-4">
        <label className="mr-2 font-medium">Select Entity Type:</label>
        <select
          className="border p-1 rounded"
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
        >
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
          <option value="new">Add New Type</option>
        </select>
      </div>

      {selectedType !== "new" && (
        <>
          {editingEntity && (
            <div className="border p-4 rounded mb-4">
              <h2 className="font-bold mb-2">
                Edit Entity: {editingEntity.id}
              </h2>
              <Textarea
                className="w-full h-32"
                value={editingJson}
                onChange={(e) => setEditingJson(e.target.value)}
              />
              <div className="mt-2 flex space-x-2">
                <Button onClick={handleUpdate}>Update</Button>
                <Button
                  variant="destructive"
                  onClick={() => setEditingEntity(null)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          <div className="border p-4 rounded">
            <h2 className="font-bold mb-2">
              Create New Entity: {selectedType}
            </h2>
            <Textarea
              className="w-full h-32"
              value={newEntityData}
              onChange={(e) => setNewEntityData(e.target.value)}
            />
            <Button className="mt-2" onClick={handleCreate}>
              Create
            </Button>
          </div>

          {entities.length === 0 && (
            <p className="mb-4">No entities found for type "{selectedType}".</p>
          )}

          <div className="mt-6">
            <Table>
              {entities.length === 0 && (
                <TableCaption>No entities found</TableCaption>
              )}
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  {dataKeys.map((key) => (
                    <TableHead key={key}>{key}</TableHead>
                  ))}
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entities.map((entity) => (
                  <TableRow key={entity.id}>
                    <TableCell>{entity.id}</TableCell>
                    {dataKeys.map((key) => (
                      <TableCell key={key}>
                        {entity.data && typeof entity.data === "object"
                          ? entity.data[key]
                          : ""}
                      </TableCell>
                    ))}
                    <TableCell className="flex space-x-2">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(entity.id)}
                      >
                        <Trash className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(entity)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {selectedType === "new" && (
        <div className="border p-4 rounded mt-6">
          <h2 className="font-bold mb-2">Create New Entity Type</h2>
          <div className="mb-4">
            <label className="mr-2 font-medium">Type Name:</label>
            <input
              className="border p-1 rounded"
              type="text"
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              placeholder="Enter new type name"
            />
          </div>
          <div className="mb-4">
            <label className="mr-2 font-medium">Schema (JSON):</label>
            <Textarea
              className="w-full h-32"
              value={newSchemaData}
              onChange={(e) => setNewSchemaData(e.target.value)}
            />
          </div>
          <Button className="mt-2" onClick={handleCreateSchema}>
            Create Type
          </Button>
        </div>
      )}
    </div>
  );
}

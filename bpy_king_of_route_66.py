'''
    3ds max's MaxScript for Importing mdl / tmb from king of route 66 on ps2

    written by mariokart64n
    dec 9 2022
    
    Script written around a dozen file samples uploaded here
    https://forum.xentax.com/viewtopic.php?p=156970#p156970

    notes:
        I was curious about the face drawing since others seemed to have issue with it.
        Looks as if the faces are written after the vertices as an array of bytes.
        when a 0 is read the face is saved, where if theres a 1:you skip basically.
        The other component to this was to read the mesh table to get the proper submeshes
        out of the vertex buffer.. kind of standard stuff.
        
        Only issue is there isn't much to the mesh table, it links into an object table
        that builds bones which I was unable to resolve. But I was able to get the mesh
        to import correctly so I was happy enough with that.
        
        Script was only tested on the samples of Arizona, so theres a high chance the
        script won't work on anything.
        
        
'''

useOpenDialog = True


from pathlib import Path  # Needed for os stuff
import random
import struct  # Needed for Binary Reader
import bpy
import mathutils  # this i'm guessing is a branch of the bpy module specifically for math operations

signed, unsigned = 0, 1  # Enums for read function
seek_set, seek_cur, seek_end = 0, 1, 2  # Enums for seek function

class bit:
    def And(integer1, integer2): return (integer1 & integer2)
    def IntAsChar(integer): return chr(int(integer))

class matrix3:
    row1 = [1.0, 0.0, 0.0]
    row2 = [0.0, 1.0, 0.0]
    row3 = [0.0, 0.0, 1.0]
    row4 = [0.0, 0.0, 0.0]

    def __init__(self, rowA=[1.0, 0.0, 0.0], rowB=[0.0, 1.0, 0.0], rowC=[0.0, 0.0, 1.0], rowD=[0.0, 0.0, 0.0]):
        if rowA == 0:
            self.row1 = [0.0, 0.0, 0.0]
            self.row2 = [0.0, 0.0, 0.0]
            self.row3 = [0.0, 0.0, 0.0]

        elif rowA == 1:
            self.row1 = [1.0, 0.0, 0.0]
            self.row2 = [0.0, 1.0, 0.0]
            self.row3 = [0.0, 0.0, 1.0]
            self.row4 = [0.0, 0.0, 0.0]
        else:
            self.row1 = rowA
            self.row2 = rowB
            self.row3 = rowC
            self.row4 = rowD

    def __repr__(self):
        return (
                "matrix3([" + str(self.row1[0]) +
                ", " + str(self.row1[1]) +
                ", " + str(self.row1[2]) +
                "], [" + str(self.row2[0]) +
                ", " + str(self.row2[1]) +
                ", " + str(self.row2[2]) +
                "], [" + str(self.row3[0]) +
                ", " + str(self.row3[1]) +
                ", " + str(self.row3[2]) +
                "], [" + str(self.row4[0]) +
                ", " + str(self.row4[1]) +
                ", " + str(self.row4[2]) + "])"
        )


def findItem(array, value):
    index = -1
    try: index = array.index(value)
    except: pass
    return index


def append(array, value):
    array.append(value)
    return None

class fopen:
    little_endian = True
    file = ""
    mode = 'rb'
    data = bytearray()
    size = 0
    pos = 0
    isGood = False

    def __init__(self, filename=None, mode='rb', isLittleEndian=True):
        if mode == 'rb':
            if filename != None and Path(filename).is_file():
                self.data = open(filename, mode).read()
                self.size = len(self.data)
                self.pos = 0
                self.mode = mode
                self.file = filename
                self.little_endian = isLittleEndian
                self.isGood = True
        else:
            self.file = filename
            self.mode = mode
            self.data = bytearray()
            self.pos = 0
            self.size = 0
            self.little_endian = isLittleEndian
            self.isGood = False

        pass

    # def __del__(self):
    #    self.flush()

    def resize(self, dataSize=0):
        if dataSize > 0:
            self.data = bytearray(dataSize)
        else:
            self.data = bytearray()
        self.pos = 0
        self.size = dataSize
        self.isGood = False
        return None

    def flush(self):
        if self.file != "" and not self.isGood and len(self.data) > 0:
            self.isGood = True
            s = open(self.file, 'w+b')
            s.write(self.data)
            s.close()

    def read_and_unpack(self, unpack, size):
        value = 0
        if self.size > 0 and self.pos + size <= self.size:
            value = struct.unpack_from(unpack, self.data, self.pos)[0]
            self.pos += size
        return value

    def pack_and_write(self, pack, size, value):
        if self.pos + size > self.size:
            self.data.extend(b'\x00' * ((self.pos + size) - self.size))
            self.size = self.pos + size
        try:
            struct.pack_into(pack, self.data, self.pos, value)
        except:
            # print('Pos:\t%i / %i (buf:%i) [val:%i:%i:%s]' % (self.pos, self.size, len(self.data), value, size, pack))
            pass
        self.pos += size
        return None

    def set_pointer(self, offset):
        self.pos = offset
        return None

    def set_endian(self, isLittle=True):
        self.little_endian = isLittle
        return isLittle


def fclose(bitStream=fopen()):
    bitStream.flush()
    bitStream.isGood = False


def fseek(bitStream=fopen(), offset=0, dir=0):
    if dir == 0:
        bitStream.set_pointer(offset)
    elif dir == 1:
        bitStream.set_pointer(bitStream.pos + offset)
    elif dir == 2:
        bitStream.set_pointer(bitStream.pos - offset)
    return None


def ftell(bitStream=fopen()):
    return bitStream.pos


def readByte(bitStream=fopen(), isSigned=0):
    fmt = 'b' if isSigned == 0 else 'B'
    return (bitStream.read_and_unpack(fmt, 1))


def readShort(bitStream=fopen(), isSigned=0):
    fmt = '>' if not bitStream.little_endian else '<'
    fmt += 'h' if isSigned == 0 else 'H'
    return (bitStream.read_and_unpack(fmt, 2))


def readLong(bitStream=fopen(), isSigned=0):
    fmt = '>' if not bitStream.little_endian else '<'
    fmt += 'i' if isSigned == 0 else 'I'
    return (bitStream.read_and_unpack(fmt, 4))

def readFloat(bitStream=fopen()):
    fmt = '>f' if not bitStream.little_endian else '<f'
    return (bitStream.read_and_unpack(fmt, 4))


def mesh_validate(vertices=[], faces=[]):
    # basic face index check
    # blender will crash if the mesh data is bad

    # Check an Array was given
    result = (type(faces).__name__ == "tuple" or type(faces).__name__ == "list")
    if result == True:

        # Check the the array is Not empty
        if len(faces) > 0:

            # check that the face is a vector
            if (type(faces[0]).__name__ == "tuple" or type(faces[0]).__name__ == "list"):

                # Calculate the Max face index from supplied vertices
                face_min = 0
                face_max = len(vertices) - 1

                # Check face indeices
                for face in faces:
                    for side in face:

                        # Check face index is in range
                        if side < face_min and side > face_max:
                            print("MeshValidation: \tFace Index Out of Range:\t[%i / %i]" % (side, face_max))
                            result = False
                            break
            else:
                print("MeshValidation: \tFace In Array is Invalid")
                result = False
        else:
            print("MeshValidation: \tFace Array is Empty")
    else:
        print("MeshValidation: \tArray Invalid")
        result = False
    return result


def mesh(
        vertices=[],
        faces=[],
        materialIDs=[],
        tverts=[],
        normals=[],
        colours=[],
        materials=[],
        mscale=1.0,
        flipAxis=False,
        obj_name="Object",
        lay_name='',
        position=(0.0, 0.0, 0.0)
        ):
    #
    # This function is pretty, ugly
    # imports the mesh into blender
    #
    # Clear Any Object Selections
    # for o in bpy.context.selected_objects: o.select = False
    bpy.context.view_layer.objects.active = None

    # Get Collection (Layers)
    if lay_name != '':
        # make collection
        layer = bpy.data.collections.get(lay_name)
        if layer == None:
            layer = bpy.data.collections.new(lay_name)
            bpy.context.scene.collection.children.link(layer)
    else:
        if len(bpy.data.collections) == 0:
            layer = bpy.data.collections.new("Collection")
            bpy.context.scene.collection.children.link(layer)
        else:
            try:
                layer = bpy.data.collections[bpy.context.view_layer.active_layer_collection.name]
            except:
                layer = bpy.data.collections[0]

    # make mesh
    msh = bpy.data.meshes.new('Mesh')

    # msh.name = msh.name.replace(".", "_")

    # Apply vertex scaling
    # mscale *= bpy.context.scene.unit_settings.scale_length
    vertArray = []
    if len(vertices) > 0:
        vertArray = [[float] * 3] * len(vertices)
        if flipAxis:
            for v in range(0, len(vertices)):
                vertArray[v] = (
                    vertices[v][0] * mscale,
                    -vertices[v][2] * mscale,
                    vertices[v][1] * mscale
                )
        else:
            for v in range(0, len(vertices)):
                vertArray[v] = (
                    vertices[v][0] * mscale,
                    vertices[v][1] * mscale,
                    vertices[v][2] * mscale
                )

    # assign data from arrays
    if not mesh_validate(vertArray, faces):
        # Erase Mesh
        msh.user_clear()
        bpy.data.meshes.remove(msh)
        print("Mesh Deleted!")
        return None

    msh.from_pydata(vertArray, [], faces)

    # set surface to smooth
    msh.polygons.foreach_set("use_smooth", [True] * len(msh.polygons))

    # Set Normals
    if len(faces) > 0:
        if len(normals) > 0:
            msh.use_auto_smooth = True
            if len(normals) == (len(faces) * 3):
                msh.normals_split_custom_set(normals)
            else:
                normArray = [[float] * 3] * (len(faces) * 3)
                if flipAxis:
                    for i in range(0, len(faces)):
                        for v in range(0, 3):
                            normArray[(i * 3) + v] = (
                                [normals[faces[i][v]][0],
                                 -normals[faces[i][v]][2],
                                 normals[faces[i][v]][1]]
                            )
                else:
                    for i in range(0, len(faces)):
                        for v in range(0, 3):
                            normArray[(i * 3) + v] = (
                                [normals[faces[i][v]][0],
                                 normals[faces[i][v]][1],
                                 normals[faces[i][v]][2]]
                            )
                msh.normals_split_custom_set(normArray)

        # create texture corrdinates
        # print("tverts ", len(tverts))
        # this is just a hack, i just add all the UVs into the same space <<<
        if len(tverts) > 0:
            uvw = msh.uv_layers.new()
            # if len(tverts) == (len(faces) * 3):
            #    for v in range(0, len(faces) * 3):
            #        msh.uv_layers[uvw.name].data[v].uv = tverts[v]
            # else:
            uvwArray = [[float] * 2] * len(tverts[0])
            for i in range(0, len(tverts[0])):
                uvwArray[i] = [0.0, 0.0]

            for v in range(0, len(tverts[0])):
                for i in range(0, len(tverts)):
                    uvwArray[v][0] += tverts[i][v][0]
                    uvwArray[v][1] += 1.0 - tverts[i][v][1]

            for i in range(0, len(faces)):
                for v in range(0, 3):
                    msh.uv_layers[uvw.name].data[(i * 3) + v].uv = (
                        uvwArray[faces[i][v]][0],
                        uvwArray[faces[i][v]][1]
                    )

        # create vertex colours
        if len(colours) > 0:
            col = msh.vertex_colors.new()
            if len(colours) == (len(faces) * 3):
                for v in range(0, len(faces) * 3):
                    msh.vertex_colors[col.name].data[v].color = colours[v]
            else:
                colArray = [[float] * 4] * (len(faces) * 3)
                for i in range(0, len(faces)):
                    for v in range(0, 3):
                        msh.vertex_colors[col.name].data[(i * 3) + v].color = colours[faces[i][v]]
        else:
            # Use colours to make a random display
            col = msh.vertex_colors.new()
            random_col = random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), 1.0
            for v in range(0, len(faces) * 3):
                msh.vertex_colors[col.name].data[v].color = random_col

    # Create Face Maps?
    # msh.face_maps.new()

    # Check mesh is Valid
    # Without this blender may crash!!! lulz
    # However the check will throw false positives so
    # an additional or a replacement valatiation function
    # would be required

    if msh.validate(clean_customdata=False):
        print("Warning, Blender Deleted (" + obj_name + "), reason unspecified, likely empty")

    # Update Mesh
    msh.update()

    # Assign Mesh to Object
    obj = bpy.data.objects.new(obj_name, msh)
    obj.location = position
    # obj.name = obj.name.replace(".", "_")

    for i in range(0, len(materials)):
        if len(obj.material_slots) < (i + 1):
            # if there is no slot then we append to create the slot and assign
            if type(materials[i]).__name__ == 'StandardMaterial':
                obj.data.materials.append(materials[i].data)
            else:
                obj.data.materials.append(materials[i])
        else:
            # we always want the material in slot[0]
            if type(materials[i]).__name__ == 'StandardMaterial':
                obj.material_slots[0].material = materials[i].data
            else:
                obj.material_slots[0].material = materials[i]
        # obj.active_material = obj.material_slots[i].material

    if len(materialIDs) == len(obj.data.polygons):
        for i in range(0, len(materialIDs)):
            obj.data.polygons[i].material_index = materialIDs[i]
            if materialIDs[i] > len(materialIDs):
                materialIDs[i] = materialIDs[i] % len(materialIDs)

    elif len(materialIDs) > 0:
        print("Error:\tMaterial Index Out of Range")

    layer.objects.link(obj)
    
    # Assign Material ID's
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.context.tool_settings.mesh_select_mode = [False, False, True]

    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def deleteScene(include=[]):
    if len(include) > 0:
        # Exit and Interactions
        if bpy.context.view_layer.objects.active != None:
            bpy.ops.object.mode_set(mode='OBJECT')

        # Select All
        bpy.ops.object.select_all(action='SELECT')

        # Loop Through Each Selection
        for o in bpy.context.view_layer.objects.selected:
            for t in include:
                if o.type == t:
                    bpy.data.objects.remove(o, do_unlink=True)
                    break

        # De-Select All
        bpy.ops.object.select_all(action='DESELECT')
    return None


class fmtTMB_Entry_0x01:  # 96 bytes, material
    '''float[4]'''
    unk115 = [0.0, 0.0, 0.0, 1.0] # Diffuse Colour RGBA
    
    '''float[4]'''
    unk116 = [1.0, 1.0, 1.0, 1.0] # Ambient Colour RGBA
    
    '''float[4]'''
    unk117 = [0.0, 0.0, 0.0, 1.0] # Emissive Colour RGBA
    
    '''float[4]'''
    unk118 = [1.0, 1.0, 1.0, 0.0] # Specular Colour RGBA
    
    '''uint32_t'''
    unk119 = 0 # Specular Power?
    
    '''uint16_t'''
    unk120 = 0
    
    '''uint16_t'''
    unk121 = 0
    
    '''uint16_t'''
    unk122 = 0
    
    '''uint16_t'''
    unk123 = 0
    
    '''uint32_t'''
    unk124 = 0
    
    '''uint32_t'''
    unk125 = 0
    
    '''uint32_t'''
    unk126 = 0
    
    '''uint32_t'''
    unk127 = 0
    
    '''uint32_t'''
    unk128 = 0
    
    def read (self, f = fopen()):
        self.unk115 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        self.unk116 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        self.unk117 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        self.unk118 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        self.unk119 = readLong(f, unsigned)
        self.unk120 = readShort(f, unsigned)
        self.unk121 = readShort(f, unsigned)
        self.unk122 = readShort(f, unsigned)
        self.unk123 = readShort(f, unsigned)
        self.unk124 = readLong(f, unsigned)
        self.unk125 = readLong(f, unsigned)
        self.unk126 = readLong(f, unsigned)
        self.unk127 = readLong(f, unsigned)
        self.unk128 = readLong(f, unsigned)
        return None
        
    

class fmtTMB_Entry_0x02:  # 240 bytes, object?
    
    '''char[32]'''
    name3 = ""
    
    '''float[4][4]'''
    unk131 = [  # Transform
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
        ]
    
    '''uint32_t'''
    unk0132 = 0.0
    
    '''uint32_t'''
    unk0133 = 0.0
    
    '''uint32_t'''
    unk0134 = 0.0
    
    '''uint32_t'''
    unk0135 = 0.0
    
    '''uint32_t'''
    unk0136 = 0.0
    
    '''uint32_t'''
    unk0137 = 0.0
    
    '''uint32_t'''
    unk0138 = 0.0
    
    '''uint32_t'''
    unk0139 = 0.0
    
    '''uint32_t'''
    unk0140 = 0.0
    
    '''uint32_t'''
    unk0141 = 0.0
    
    '''uint32_t'''
    unk0142 = 0.0
    
    '''uint32_t'''
    unk0143 = 0.0
    
    '''uint32_t'''
    unk0144 = 0.0
    
    '''uint32_t'''
    unk0145 = 0.0
    
    '''uint32_t'''
    unk0146 = 0.0
    
    '''uint32_t'''
    unk0147 = 0.0
    
    '''uint32_t'''
    unk0148 = 0.0
    
    '''uint32_t'''
    unk0149 = 0.0
    
    '''uint32_t'''
    unk0150 = 0.0
    
    '''uint32_t'''
    unk0151 = 0.0
    
    '''uint32_t'''
    unk0152 = 0.0
    
    '''uint32_t'''
    unk0153 = 0.0
    
    '''uint32_t'''
    unk0154 = 0.0
    
    '''uint32_t'''
    unk0155 = 0.0
    
    '''uint32_t'''
    unk0156 = 0.0
    
    '''uint32_t'''
    unk0157 = 0.0
    
    '''uint32_t'''
    unk0158 = 0.0
    
    '''uint32_t'''
    unk0159 = 0.0
    
    '''uint32_t'''
    unk0160 = 0.0
    
    '''uint32_t'''
    unk0161 = 0.0
    
    '''uint32_t'''
    unk0162 = 0.0
    
    '''uint32_t'''
    unk0163 = 0.0
    
    '''int32_t'''
    unk0164 = -1
    
    '''int32_t'''
    unk0165 = -1 # -1 parent?
    
    '''int32_t'''
    unk0166 = -1 # -1 index?
    
    '''uint32_t'''
    unk0167 = 0 # padding probably
    
    def readFixedString (self, f = fopen(), len = 0):
        str = ""
        p = ftell(f) + len
        for i in range(0, len):
            b = readByte(f, unsigned)
            if b > 0:
                str += bit.IntAsChar(b)
            else: break
        fseek(f,p, seek_set)
        return str
        
    
    def read (self, f = fopen()):
        self.name3 = self.readFixedString(f, 32)
        
        # matrix?
        self.unk131 = [
            [readFloat(f), readFloat(f), readFloat(f), readFloat(f)], # 1 0 0 0
            [readFloat(f), readFloat(f), readFloat(f), readFloat(f)], # 0 1 0 0
            [readFloat(f), readFloat(f), readFloat(f), readFloat(f)], # 0 0 1 0
            [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]  # 0 0 0 1
            ]
        
        self.unk0132 = readFloat(f)
        self.unk0133 = readFloat(f)
        self.unk0134 = readFloat(f)
        self.unk0135 = readFloat(f) # 1.0
        
        # empty
        self.unk0136 = readFloat(f)
        self.unk0137 = readFloat(f)
        self.unk0138 = readFloat(f)
        self.unk0139 = readFloat(f)
        self.unk0140 = readFloat(f)
        self.unk0141 = readFloat(f)
        self.unk0142 = readFloat(f)
        self.unk0143 = readFloat(f)
        self.unk0144 = readFloat(f)
        self.unk0145 = readFloat(f)
        self.unk0146 = readFloat(f)
        self.unk0147 = readFloat(f)
        self.unk0148 = readFloat(f)
        self.unk0149 = readFloat(f)
        self.unk0150 = readFloat(f)
        self.unk0151 = readFloat(f)
        
        # transform?
        self.unk0152 = readFloat(f)
        self.unk0153 = readFloat(f)
        self.unk0154 = readFloat(f)
        self.unk0155 = readFloat(f)
        
        self.unk0156 = readFloat(f)
        self.unk0157 = readFloat(f)
        self.unk0158 = readFloat(f)
        self.unk0159 = readFloat(f)
        
        self.unk0160 = readFloat(f)
        self.unk0161 = readFloat(f)
        self.unk0162 = readFloat(f)
        self.unk0163 = readFloat(f) # 1.0
        
        self.unk0164 = readLong(f, signed)
        self.unk0165 = readLong(f, signed) # -1
        self.unk0166 = readLong(f, signed) # -1
        self.unk0167 = readLong(f, unsigned)
        return None
        
    

class fmtTMB_Entry_0x03:  # 48 bytes, ??
    unk080 = 0
    unk081 = 0
    unk082 = 0
    unk083 = 0.0
    unk084 = 0.0
    unk085 = 0.0
    unk086 = 0.0
    unk087 = 0.0
    unk088 = 0
    unk089 = 0
    unk090 = 0
    unk091 = 0
    def read (self, f = fopen()):
        self.unk080 = readLong(f, unsigned)
        self.unk081 = readLong(f, unsigned)
        self.unk082 = readLong(f, unsigned)
        self.unk083 = readFloat(f)
        self.unk084 = readFloat(f)
        self.unk085 = readFloat(f)
        self.unk086 = readFloat(f)
        self.unk087 = readFloat(f)
        self.unk088 = readLong(f, unsigned)
        self.unk089 = readLong(f, unsigned)
        self.unk090 = readLong(f, unsigned)
        self.unk091 = readLong(f, unsigned)
        return None
        
    

class fmtTMB_Entry_0x04:  # 32 bytes, mesh info? verts counts etc
    '''uint32_t'''
    unk0168 = 0
    
    '''uint32_t'''
    unk0169 = 0 # 3
    
    '''uint32_t'''
    unk0170 = 0
    
    '''uint32_t'''
    unk0171 = 0
    
    '''uint32_t'''
    unk0172 = 0
    
    '''uint32_t'''
    unk0173 = 0
    
    '''uint32_t'''
    unk0174 = 0
    
    '''uint32_t'''
    unk0175 = 0 # 0 probably padding
    
    def read (self, f = fopen()):
        self.unk0168 = readLong(f, unsigned)
        self.unk0169 = readLong(f, unsigned) # 3
        self.unk0170 = readLong(f, unsigned)
        self.unk0171 = readLong(f, unsigned)
        self.unk0172 = readLong(f, unsigned)
        self.unk0173 = readLong(f, unsigned)
        self.unk0174 = readLong(f, unsigned)
        self.unk0175 = readLong(f, unsigned)
        return None
        
    
    
    

class fmtTMB_Entry_0x05:  # 32 bytes, vertex position, normal
    '''
        vertices are in world space, yay no need to transform them
    '''
    '''float[4]'''
    unk0180 = [0.0, 0.0, 0.0, 1.0] # Position
    
    '''float[4]'''
    unk0181 = [0.0, 0.0, 0.0, 1.0] # Normal
    
    def read (self, f = fopen()):
        self.unk0180 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        self.unk0181 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        return None
        
    
    

class fmtTMB_Entry_0x06:  # 16 bytes, Vertex Positions Again lol
    '''float[4]'''
    unk0191 = [0.0, 0.0, 0.0, 0.0] # Position
    
    def read (self, f = fopen()):
        self.unk0191 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        return None
        
    

#class fmtTMB_Entry_0x07 uint8_t b # weird boolean table

class fmtTMB_Entry_0x08:  # 16 bytes, Normals Again
    '''float[4]'''
    unk0192 = [0.0, 0.0, 0.0, 0.0]
    
    def read (self, f = fopen()):
        self.unk0192 = [readFloat(f), readFloat(f), readFloat(f), readFloat(f)]
        return None
        
    

class fmtTMB_Entry_0x0B:
    '''uint32_t'''
    type = 0
    
    '''uint32_t'''
    unk0200 = []
    
    def read (self, f = fopen()):
        '''
        need to review more samples,
        
        looks like its an array of ints,
        and it the int is bitmasked with 0x80
        then you start reading a new array to
        stream into..
        
        however theres some ints and floats so
        i had figured there was a type specifier
        but i'm unsure...
        
        i'll have to look at smaller samples to
        quantify the patterns in the stream..
        
        '''
        return None
        
    

#class fmtTMB_Entry_0x0C 

class fmtTMB_Table3_Entry:  # 32 bytes
    '''uint32_t'''
    unk0181 = 0 # vertex size
    
    '''uint32_t'''
    unk0182 = 0 # 3
    
    '''uint32_t'''
    unk0183 = 0 # index?
    
    '''uint32_t'''
    unk0184 = 0 # 1. vertex position
    
    '''uint32_t'''
    unk0185 = 0 # 2. ? position
    
    '''uint32_t'''
    unk0186 = 0 # 3. normal position
    
    '''uint32_t'''
    unk0187 = 0 # 4. ? position
    
    '''uint32_t'''
    unk0188 = 0 # 5. ? position
    
    def read_table3_entry (self, f = fopen()):
        self.unk0181 = readLong(f, unsigned)
        self.unk0182 = readLong(f, unsigned)
        self.unk0183 = readLong(f, unsigned)
        self.unk0184 = readLong(f, unsigned)
        self.unk0185 = readLong(f, unsigned)
        self.unk0186 = readLong(f, unsigned)
        self.unk0187 = readLong(f, unsigned)
        self.unk0188 = readLong(f, unsigned)
        return None
        
    

class fmtTMB_Addr:  # 8 bytes
    '''uint32_t'''
    addr = 0 # multiply by 16
    
    '''uint32_t'''
    count = 0
    
    def read (self, f = fopen()):
        self.addr = readLong(f, unsigned)
        self.count = readLong(f, unsigned)
        return None
        
    

class fmtTMB:
    '''uint32_t'''
    type = 0x20424D54
    
    '''uint32_t'''
    unk101 = 0
    
    '''float'''
    unk102 = 0.0
    
    '''fmtTMB_Addr[13]'''
    addrs = []
    
    '''char[64]'''
    textures = []
    
    '''fmtTMB_Entry_0x01[]'''
    boneArray = []
    
    '''fmtTMB_Entry_0x02[]'''
    objArray = []
    
    '''fmtTMB_Entry_0x03[]'''
    mshArray = []
    
    #0x04
    '''fmtTMB_Entry_0x05[]'''
    vertArray = []
    
    '''fmtTMB_Entry_0x06[]'''
    unk0190Array = []
    
    '''uint8_t[]'''
    flagArray = []
    
    '''fmtTMB_Entry_0x08[]'''
    unk0193Array = []
    
    '''uint16_t[]'''
    unk0195Array = []
    
    def readFixedString (self, f = fopen(), len = 0):
        str = ""
        p = ftell(f) + len
        for i in range(0, len):
            b = readByte(f, unsigned)
            if b > 0:
                str += bit.IntAsChar(b)
            else: break
        fseek(f,p, seek_set)
        return str
        
    
    def readFaces(self, pos = 0, count = 0):
        Face_array = []	
        if count > 0:
            face = [0, 1, 2]
            counter = 0
            j = 1
            for j in range(0, len(self.flagArray)):
                face = [face[1], face[2], counter]
                if face[0] >= count or face[1] >= count or face[2] >= count:
                    break
                counter += 1
                if self.flagArray[j + pos] == 0:
                    if bit.And(j, 1):
                        append(Face_array, [face[0], face[2], face[1]])
                    else:
                        append(Face_array, [face[0], face[1], face[2]])
        return Face_array
        
    
    def read (self, f = fopen()):
        
        # get start of file
        pos = ftell(f)
        
        # Read header
        self.type = readLong(f, unsigned)
        self.unk101 = readLong(f, unsigned)
        self.unk102 = readFloat(f)
        
        # Read Block Table
        self.addrs = []
        self.num_addrs = 13
        self.addrs = [fmtTMB_Addr] * self.num_addrs
        
        
        
        
        self.textures = []
        self.boneArray = []
        self.objArray = []
        self.mshArray = []
        self.vertArray = []
        self.unk0190Array = []
        self.flagArray = []
        self.unk0193Array = []
        self.unk0195Array = []
        for i in range(0, self.num_addrs):
            
            
            # seek to table entry
            fseek(f, pos + 12 + i * 8, seek_set)
            
            # Init Array Element
            self.addrs[i] = fmtTMB_Addr()
            
            # Read Entry
            self.addrs[i].read(f)
            
            # Skip if address is null
            if self.addrs[i].addr == 0: continue
            
            # Read Block
            fseek(f,pos + self.addrs[i].addr * 16, seek_set)
            count = self.addrs[i].count
            if count > 0:
                    
                if i == 0x00: # Texture Names
                    self.textures = [str] * count
                    for j in range(0, count):
                        self.textures[j] = self.readFixedString(f, 64)
                        
                        
                    
                elif i == 0x01:  # Bones, Probably...
                    self.boneArray = [fmtTMB_Entry_0x01] * count
                    for j in range(0, count):
                        self.boneArray[j] = fmtTMB_Entry_0x01()
                        self.boneArray[j].read(f)
                            
                        
                    
                elif i == 0x02:  # Object
                    self.objArray = [fmtTMB_Entry_0x02] * count
                    for j in range(0, count):
                        self.objArray[j] = fmtTMB_Entry_0x02()
                        self.objArray[j].read(f)
                            
                        
                    
                elif i == 0x03: 
                    # need to examine other samples
                    pass
                    
                elif i == 0x04:  # Mesh Info
                    self.mshArray = [fmtTMB_Entry_0x04] * count
                    for j in range(0, count):
                        self.mshArray[j] = fmtTMB_Entry_0x04()
                        self.mshArray[j].read(f)
                        #self.mshArray[j].repr
                            
                        
                    
                elif i == 0x05:  # Vertex Positions, hm maybe this used for lookup
                    self.vertArray = [fmtTMB_Entry_0x05] * count
                    for j in range(0, count):
                        self.vertArray[j] = fmtTMB_Entry_0x05()
                        self.vertArray[j].read(f)
                                
                        
                    
                    
                    
                elif i == 0x06:  # Vertices Again
                    
                    count = int(count / 16)
                    if count > 0:
                        self.unk0190Array = [fmtTMB_Entry_0x06] * count
                        for j in range(0, count):
                            self.unk0190Array[j] = fmtTMB_Entry_0x06()
                            self.unk0190Array[j].read(f)
                            
                        
                    
                elif i == 0x07:  # Faces
                    
                    self.flagArray = []
                    self.flagArray = [int] * count
                    for j in range(0, count):
                        self.flagArray[j] = readByte(f, unsigned)
                            
                        
                        
                    
                    
                elif i == 0x08:  # Normals Again
                    count = int(count / 16)
                    if count > 0:
                        self.unk0193Array = [fmtTMB_Entry_0x08] * count
                        for j in range(0, count):
                            self.unk0193Array[j] = fmtTMB_Entry_0x08()
                            self.unk0193Array[j].read(f)
                            
                        
                    
                elif i == 0x09:  # texture corrdinates maybe??
                    count = int(count / 4.0)
                    if count > 0:
                        self.unk0195Array = [[float] * 3] * count
                        for j in range(0, count):
                            self.unk0195Array[j] = [readShort(f, unsigned) / 1024.0, readShort(f, unsigned) / 1024.0, 0.0]
                            
                        
                    
                elif i == 0x0A: 
                    # not present in my sample, need to review more samples
                    pass
                    
                elif i == 0x0B:  # some sort of data stream
                    #fmtTMB_Entry_0x0B
                    pass
                    
                elif i == 0x0C: 
                    # need to examine more samples, not alot data is present at this block
                    pass
            
        return None
                
            
            
        
    
    def build (self, clear_scene = False, mscale = 0.1, buildBones = False):
        
        # ClearScene
        if clear_scene == True: deleteScene(['MESH', 'ARMATURE'])
        
        
        # Loop Through object
        o = None
        t = matrix3(1)
        d = None
        msh = None
        bnsArray = []
        vertices = []
        tvertices = []
        faceArray = []
        faceStart = 0
        j = 1
        v = 1
        uvStart = 0
        for j in range(0, len(self.mshArray)):
            # Mesh
            
            vertices = []
            faceArray = []
            
            # if no vertices,:SKIP
            if self.mshArray[j].unk0168 == 0: continue
            
            # Read Faces
            faceArray = self.readFaces(faceStart, self.mshArray[j].unk0168)
            faceStart += (self.mshArray[j].unk0168 + ((16-(self.mshArray[j].unk0168 % 16)) % 16))
            
            
            # Read Vertices
            vertices = []
            tvertices = []
            vertices = [[float] * 3] * self.mshArray[j].unk0168
            tvertices = [[float] * 3] * self.mshArray[j].unk0168
            
            vp = self.mshArray[j].unk0171 + self.mshArray[j].unk0168 - self.mshArray[j].unk0171
            for v in range(self.mshArray[j].unk0171,  self.mshArray[j].unk0171 + self.mshArray[j].unk0168):
                vertices[v - self.mshArray[j].unk0171] = [self.unk0190Array[v].unk0191[0] * mscale, -self.unk0190Array[v].unk0191[2] * mscale, self.unk0190Array[v].unk0191[1] * mscale]
                
            
            for v in range(0, vp):
                vt = (v + uvStart) % self.mshArray[j].unk0168
                tvertices[v] = [self.unk0195Array[vt][0], self.unk0195Array[vt][1], 0.0]
                
                
                
            uvStart += int(((self.mshArray[j].unk0168 * 4) + ((16-((self.mshArray[j].unk0168 * 4) % 16)) % 16)) / 4.0)
            
            
            # Build Mesh
            msh = mesh(
                vertices=vertices,
                faces=faceArray,
                tverts=[tvertices]
                )
            
            #msh.transform = t
            #append(mdls msh
            
        
        
        
        if buildBones:
            # Build Bones
            for o in self.objArray:
                
                # Bone
                '''
                d = Dummy name:o.name3 boxSize:[0.25, 0.25, 0.25] transform:
                    matrix3 \
                        [o.unk131[1][1], o.unk131[1][2], o.unk131[1][3]] + o.unk131[1][4] \
                        [o.unk131[2][1], o.unk131[2][2], o.unk131[2][3]] + o.unk131[2][4] \
                        [o.unk131[3][1], o.unk131[3][2], o.unk131[3][3]] + o.unk131[3][4] \
                        [o.unk131[4][1], o.unk131[4][2], o.unk131[4][3]] * mscale * o.unk131[4][4]
                    
                d.showLinks = d.showLinksOnly = True
                append(bnsArray d
                '''
            
            i = 1
            par = 1
            pos = [0.0, 0.0, 0.0]
            for i in range(0, len(bnsArray)):
                
                
                par = self.objArray[i].unk0166
                if par > -1:
                    t = bnsArray[i].transform
                    pos = bnsArray[i].position
                    while par > -1:
                        t *= bnsArray[par].transform 
                        pos += bnsArray[par].position
                        
                        
                        par = self.objArray[par].unk0166
                        break
                        
                    bnsArray[i].transform = t
                    #bnsArray[i].position = pos
                    
                    bnsArray[i].parent = bnsArray[self.objArray[i].unk0166] 
        return None
                    
                
                
                

class fmtP2IG:
    '''uint32_t'''
    type = 0x47493250 # P2IG
    
    '''uint32_t'''
    unk001 = 0
    
    '''uint32_t'''
    unk002 = 0
    
    '''uint16_t'''
    unk003 = 0
    
    '''uint16_t'''
    unk004 = 0
    
    '''char[8]'''
    name = ""
    
    '''uint32_t'''
    unk005 = 0
    
    '''uint32_t'''
    unk006 = 0
    
    '''uint16_t'''
    unk007 = 0 # width
    
    '''uint16_t'''
    unk008 = 0 # length
    
    '''uint32_t'''
    unk009 = 0 # type 0x13 = 8bit 0x14 = 4bit?
    
    '''uint32_t'''
    unk010 = 0
    
    '''uint32_t'''
    unk011 = 0
    
    '''uint32_t'''
    unk012 = 0
    
    '''uint32_t'''
    unk013 = 0
    
    '''uint32_t'''
    unk014 = 0
    
    '''uint32_t'''
    unk015 = 0
    
    '''uint32_t'''
    unk016 = 0 # pal pos
    
    '''uint32_t'''
    unk017 = 0 # pal size
    
    '''uint32_t'''
    unk018 = 0 # img pos
    
    '''uint32_t'''
    unk019 = 0 # img size
    
    '''uint32_t'''
    unk020 = 0
    
    '''uint32_t'''
    unk021 = 0
    
    '''uint32_t'''
    unk022 = 0
    
    '''uint32_t'''
    unk023 = 0
    
    '''uint32_t'''
    unk024 = 0
    
    '''uint32_t'''
    unk025 = 0
    
    '''uint32_t'''
    unk026 = 0
    
    '''uint32_t'''
    unk027 = 0
    
    '''uint32_t'''
    unk028 = 0
    
    '''uint32_t'''
    unk029 = 0
    
    '''uint32_t'''
    unk030 = 0
    
    '''uint32_t'''
    unk031 = 0
    
    '''uint8_t[4][]'''
    pal = []
    
    '''uint8_t[]'''
    img = []
    
    '''
        ps2 unswizzle code courtesy of TopazTK,
        while I was working on soul calibur 3
        
        https://forum.xentax.com/viewtopic.php?t=22497
    '''
    
    def readFixedString (self, f = fopen(), len = 0):
        str = ""
        p = ftell(f) + len
        for i in range(0, len):
            b = readByte(f, unsigned)
            if b > 0:
                str += bit.IntAsChar(b)
            else: break
        fseek(f, p, seek_set)
        return str
        
    
    def read (self, f = fopen()):
        
        self.type = readLong(f, unsigned)
        self.unk001 = readLong(f, unsigned)
        self.unk002 = readLong(f, unsigned)
        self.unk003 = readShort(f, unsigned)
        self.unk004 = readShort(f, unsigned)
        self.name = self.readFixedString(f, 8)
        self.unk005 = readLong(f, unsigned)
        self.unk006 = readLong(f, unsigned)
        self.unk007 = readShort(f, unsigned)
        self.unk008 = readShort(f, unsigned)
        self.unk009 = readLong(f, unsigned)
        self.unk010 = readLong(f, unsigned)
        self.unk011 = readLong(f, unsigned)
        self.unk012 = readLong(f, unsigned)
        self.unk013 = readLong(f, unsigned)
        self.unk014 = readLong(f, unsigned)
        self.unk015 = readLong(f, unsigned)
        self.unk016 = readLong(f, unsigned)
        self.unk017 = readLong(f, unsigned)
        self.unk018 = readLong(f, unsigned)
        self.unk019 = readLong(f, unsigned)
        self.unk020 = readLong(f, unsigned)
        self.unk021 = readLong(f, unsigned)
        self.unk022 = readLong(f, unsigned)
        self.unk023 = readLong(f, unsigned)
        self.unk024 = readLong(f, unsigned)
        self.unk025 = readLong(f, unsigned)
        self.unk026 = readLong(f, unsigned)
        self.unk027 = readLong(f, unsigned)
        self.unk028 = readLong(f, unsigned)
        self.unk029 = readLong(f, unsigned)
        self.unk030 = readLong(f, unsigned)
        self.unk031 = readLong(f, unsigned)
        
        # Read Image Data
        count = int(self.unk017 / 4.0)
        self.img = []
        self.pal = []
        if count > 0:
            fseek(f, self.unk016, seek_set)
            
            for i in range(0, count):
                self.pal.append([readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned), readByte(f, unsigned)])
                
            fseek(f, self.unk018, seek_set)
            if self.unk019 > 0:
                self.img = [int] * self.unk019
                for i in range(0, self.unk019):
                    self.img[i] = readByte(f, unsigned)
        return None
    

class fmtMDL_Asset:
    '''
        this is just an intermediate between the different assets
    '''
    
    '''uint32_t'''
    type = 0
    
    '''fmtTMB'''
    model = None
    
    '''fmtP2IG'''
    texture = None
    
    def read (self, f = fopen(), fsize = 0):
        
        '''
            I include the asset size in the param 'fsize'
            as a precaution since the mdl acts as a file
            container.
        '''
        
        pos = ftell(f) # log current cursor position
        
        self.type = readLong(f, unsigned)
        fseek(f, pos, seek_set) # restore cursor position to start of asset
        
    
        if self.type == 0x20424D54:  # TMB (Model)
            self.model = fmtTMB()
            self.model.read(f)
            self.model.build()
        elif self.type == 0x47493250: # P2IG (Texture)
            self.texture = fmtP2IG()
            self.texture.read(f) # has paring issue
            #self.texture.build() # code from sc3 still needs to be adopted
            pass
        else: 
            print("Assest Unsupported")
        return None
            
            
        
    
    
    
class fmtMDL:
    
    '''uint32_t[]'''
    addrs = [], # address table is padded to 16bytes
    
    '''fmtMDL_Asset[]'''
    asset = [], # being ps2 self.assets are probably padded to 16 as well
    
    def read (self, f = fopen()):
        
        # Reset Arrays
        self.addrs = []
        self.asset = []
        
        # Get File Size
        pos = ftell(f)
        fsize = f.size
        fseek(f, pos, seek_set)
        
        # Read Address Table
        addr = 0
        eariest_addr = fsize
        while ftell(f) < eariest_addr:
            
            # Read Address
            addr = readLong(f, unsigned)
            
            # break if addr is 0
            if addr == 0: break
            
            # Log Address
            self.addrs.append(addr)
            
            # Log addr if its smaller:last addr
            if addr < eariest_addr:
                eariest_addr = addr
                
            
        
        # Get self.asset count from number of valid addresses
        count = len(self.addrs)
        if count > 0:
            
            # Generate a list of unique address, so calculate blocks sizes
            index = -1
            sizes = [fsize] #include the full size to start
            for i in range(0, count):
                # Search sizes array for the address
                index = findItem(sizes, self.addrs[i])
                
                # Not in sizes array, so append(address to it.
                if index == -1:
                    sizes.append(self.addrs[i])
                    
                
            
            # Sort sizes Array
            sizes.sort()
            
            # Dimension Asset Array
            self.asset = [fmtMDL_Asset] * count
            
            # Process Each Asset
            for i in range(0, count):
                
                # Search for ordered address in the sizes array
                index = findItem(sizes, self.addrs[i]) # index up to the next address
                
                #  Initialize Array Element
                self.asset[i] = fmtMDL_Asset()
                
                # Read Asset
                fseek(f, self.addrs[i], seek_set) # set cursor at start of self.asset
                self.asset[i].read(f, sizes[index]) # sizes[index] specifies the length of the self.asset
        return None
                
            
        
def read (file, mscale = 0.1):
    if file != None and file != "":
        
        f = fopen(file, "rb")
        if f != None:
            
            pos = ftell(f)
            
            filetype = readLong(f, unsigned)
            fseek(f, pos, seek_set)
            
            if filetype == 0x20424D54:  # TMB
                tmb = fmtTMB()
                tmb.read(f)
                tmb.build(mscale=mscale)
                
            else:  # Try MDL
                mdl = fmtMDL()
                mdl.read(f)
                
            
            
            fclose(f)
        else: print("Failed to open file")
        
    return None
    


# Callback when file(s) are selected

def kor66tmb_callback(fpath="", files=[], clearScene=True, mscale=0.1):
    if len(files) > 0 and clearScene: deleteScene(['MESH', 'ARMATURE'])
    for file in files:
        read (fpath + file.name, mscale)
    if len(files) > 0:
        #messageBox("Done!")
        return True
    else:
        return False


# Wrapper that Invokes FileSelector to open files from blender
def kor66tmb(reload=False):
    # Un-Register Operator
    if reload and hasattr(bpy.types, "IMPORTHELPER_OT_kor66tmb"):  # print(bpy.ops.importhelper.kor66tmb.idname())

        try:
            bpy.types.TOPBAR_MT_file_import.remove(
                bpy.types.Operator.bl_rna_get_subclass_py('IMPORTHELPER_OT_kor66tmb').menu_func_import)
        except:
            print("Failed to Unregister2")

        try:
            bpy.utils.unregister_class(bpy.types.Operator.bl_rna_get_subclass_py('IMPORTHELPER_OT_kor66tmb'))
        except:
            print("Failed to Unregister1")

    # Define Operator
    class ImportHelper_kor66tmb(bpy.types.Operator):

        # Operator Path
        bl_idname = "importhelper.kor66tmb"
        bl_label = "Select File"

        # Operator Properties
        # filter_glob: bpy.props.StringProperty(default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp', options={'HIDDEN'})
        filter_glob: bpy.props.StringProperty(default='*.mdl;*.tmb', options={'HIDDEN'}, subtype='FILE_PATH')

        # Variables
        filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # full path of selected item (path+filename)
        filename: bpy.props.StringProperty(subtype="FILE_NAME")  # name of selected item
        directory: bpy.props.StringProperty(subtype="FILE_PATH")  # directory of the selected item
        files: bpy.props.CollectionProperty(
            type=bpy.types.OperatorFileListElement)  # a collection containing all the selected items f filenames

        # Controls
        my_int1: bpy.props.IntProperty(name="Some Integer", description="Tooltip")
        my_float1: bpy.props.FloatProperty(name="Scale", default=0.1, description="Changes Scale of the imported Mesh")
        # my_float2: bpy.props.FloatProperty(name="Some Float point", default = 0.25, min = -0.25, max = 0.5)
        my_bool1: bpy.props.BoolProperty(name="Clear Scene", default=True, description="Deletes everything in the scene prior to importing")

        # Runs when this class OPENS
        def invoke(self, context, event):

            # Retrieve Settings
            try: self.filepath = bpy.types.Scene.kor66tmb_filepath
            except: bpy.types.Scene.kor66tmb_filepath = bpy.props.StringProperty(subtype="FILE_PATH")

            try: self.directory = bpy.types.Scene.kor66tmb_directory
            except: bpy.types.Scene.kor66tmb_directory = bpy.props.StringProperty(subtype="FILE_PATH")

            try: self.my_float1 = bpy.types.Scene.kor66tmb_my_float1
            except: bpy.types.Scene.kor66tmb_my_float1 = bpy.props.FloatProperty(default=0.1)

            try: self.my_bool1 = bpy.types.Scene.kor66tmb_my_bool1
            except: bpy.types.Scene.kor66tmb_my_bool1 = bpy.props.BoolProperty(default=False)
            

            # Open File Browser
            # Set Properties of the File Browser
            context.window_manager.fileselect_add(self)
            context.area.tag_redraw()

            return {'RUNNING_MODAL'}

        # Runs when this Window is CANCELLED
        def cancel(self, context):
            print("run bitch")

        # Runs when the class EXITS
        def execute(self, context):

            # Save Settings
            bpy.types.Scene.kor66tmb_filepath = self.filepath
            bpy.types.Scene.kor66tmb_directory = self.directory
            bpy.types.Scene.kor66tmb_my_float1 = self.my_float1
            bpy.types.Scene.kor66tmb_my_bool1 = self.my_bool1

            # Run Callback
            kor66tmb_callback(
                self.directory,
                self.files,
                self.my_bool1,
                self.my_float1
                )

            return {"FINISHED"}

            # Window Settings

        def draw(self, context):

            self.layout.row().label(text="Import Settings")

            self.layout.separator()
            self.layout.row().prop(self, "my_bool1")
            self.layout.row().prop(self, "my_float1")

            self.layout.separator()

            col = self.layout.row()
            col.alignment = 'RIGHT'
            col.label(text="  Author:", icon='QUESTION')
            col.alignment = 'LEFT'
            col.label(text="mariokart64n")

            col = self.layout.row()
            col.alignment = 'RIGHT'
            col.label(text="Release:", icon='GRIP')
            col.alignment = 'LEFT'
            col.label(text="January 3, 2023")

        def menu_func_import(self, context):
            self.layout.operator("importhelper.kor66tmb", text="King of Route 66 (*.mdl, *.tmb)")

    # Register Operator
    bpy.utils.register_class(ImportHelper_kor66tmb)
    bpy.types.TOPBAR_MT_file_import.append(ImportHelper_kor66tmb.menu_func_import)

    # Assign Shortcut key
    # bpy.context.window_manager.keyconfigs.active.keymaps["Window"].keymap_items.new('bpy.ops.text.run_script()', 'E', 'PRESS', ctrl=True, shift=False, repeat=False)

    # Call ImportHelper
    bpy.ops.importhelper.kor66tmb('INVOKE_DEFAULT')


# END OF MAIN FUNCTION ##############################################################


if not useOpenDialog:

    deleteScene(['MESH', 'ARMATURE'])
    
    read (
        "E:\\BackUp\\MyCloud4100\\Coding\\Maxscripts\\File IO\\King of Route 66, The (USA)\\ARIZONA_ARI_BODY\\ARIZONA_ARI_BODY.mdl"
        )
else: kor66tmb(True)
